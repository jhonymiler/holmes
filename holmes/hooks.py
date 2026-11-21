#!/usr/bin/env python3
"""Hooks de shell do holmes 2.0 (declarados em .claude/settings.json). Lê o evento JSON no stdin.

    abertura    SessionStart      mapa do caso ATIVO (≤ 3,5 KB) + cauda do diário após compactar/retomar
    pistas      UserPromptSubmit  até 6 linhas do banco sobre o pedido (sem repetir na sessão) + túnel + leitura pendente
    guarda      PreToolUse(Bash)  nega `pkill -f` (mata o próprio shell)
    pos         PostToolUse(Bash) script do caso rodou sem teste registrado → lembrete visível ao agente
    fim         Stop              regrava o diário; cobra registro se rodou script do caso sem chamar holmes.py
    pre-compact PreCompact        regrava o diário antes do corte

Tudo que um hook injeta fica abaixo de 10.000 caracteres: acima disso o Claude Code troca o texto por uma
prévia de 2 KB. Hook nunca quebra a sessão: qualquer erro vira silêncio + linha em stderr.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import holmes as H  # noqa: E402

ESTADO = H.RAIZ / ".holmes"
MAX_DIARIO = int(os.environ.get("HOLMES_MAX_DIARIO") or 120_000)
SCRIPT = re.compile(r"\b(?:python3?|\S*/bin/python)\b(?:\s+-\S+)*\s+([\w./-]+\.py)\b")


def saida(evento, texto):
    return {"hookSpecificOutput": {"hookEventName": evento, "additionalContext": texto[:9000]}}


def holmes(*args):
    r = subprocess.run([sys.executable, "-I", str(AQUI / "holmes.py"), *args], capture_output=True, text=True,
                       timeout=20, cwd=H.RAIZ)
    return (r.stdout or r.stderr).strip()


def diario_de(ev):
    return ESTADO / "diario" / f"{ev.get('session_id', 'sessao')}.md"


def atualiza_diario(ev):
    """Só mensagens do usuário e texto do agente (o raciocínio, ~7% da janela); comandos e saídas ficam de fora.
    Regenerado do .jsonl a cada turno, então é idempotente e sobrevive à compactação."""
    eventos, inteiro = cauda(ev["transcript_path"], 16 << 20)
    corpo = monta_diario(eventos)
    if not inteiro and len(corpo) < MAX_DIARIO * 0.9:  # cauda não bastou para encher o diário: lê tudo
        corpo = monta_diario(cauda(ev["transcript_path"], None)[0])
    alvo = diario_de(ev)
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(f"# Diário da sessão {ev.get('session_id', '?')} (gerado; não editar)\n{corpo}", encoding="utf-8")
    return alvo


def cauda(transcript, nbytes):
    """Eventos do .jsonl lendo só os últimos nbytes (None = tudo). O transcript chega a 80 MB, e ler tudo a cada
    turno custava ~4,6 s no Stop; a cauda basta quase sempre. Devolve (eventos, leu_o_arquivo_inteiro)."""
    with open(transcript, "rb") as f:
        f.seek(0, 2)
        tam = f.tell()
        ini = 0 if nbytes is None or tam <= nbytes else tam - nbytes
        f.seek(max(ini - 1, 0))
        dados = f.read()
    if ini:  # descarta só o pedaço de linha cortado (lendo 1 byte antes: se o corte caiu no início, nada se perde)
        dados = dados[dados.find(b"\n") + 1:]
    linhas = dados.decode("utf-8", errors="replace").split("\n")  # não splitlines: U+2028 é texto válido no JSON
    eventos = []
    for l in linhas:
        try:
            eventos.append(json.loads(l))
        except ValueError:
            pass
    return eventos, ini == 0


def monta_diario(eventos):
    blocos = []
    for e in eventos:
        c, q = (e.get("message") or {}).get("content"), (e.get("timestamp") or "")[:16].replace("T", " ")
        if e.get("type") == "user" and not e.get("isMeta") and not e.get("isCompactSummary"):
            for x in [c] if isinstance(c, str) else [b.get("text", "") for b in c or []
                                                     if isinstance(b, dict) and b.get("type") == "text"]:
                if x.strip():
                    blocos.append(f"\n## [{q}] usuário\n{x.strip()}")
        elif e.get("type") == "assistant":
            for b in c or []:
                if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip():
                    blocos.append(f"\n### [{q}] agente\n{b['text'].strip()}")
    corpo = ""
    for b in reversed(blocos):  # mantém o mais recente; o .jsonl guarda o resto
        if len(corpo) + len(b) > MAX_DIARIO:
            corpo = corpo or b[-MAX_DIARIO:]  # um bloco maior que o diário: guarda a cauda dele, não nada
            break
        corpo = b + corpo
    return corpo


def abertura(ev):
    try:
        caso = H.caso_ativo()
    except H.Erro as e:
        casos = ", ".join(p.parent.name for p in H.CASOS.glob("*/caso.db")) or "nenhum"
        return saida("SessionStart", f"[holmes] {e}. Casos existentes: {casos}.")
    partes = [f"[holmes] Caso ativo: {caso}. Siga primeiro o que o usuário pedir nesta mensagem; o mapa é "
              "orientação, não tarefa.", holmes("mapa")]
    d = diario_de(ev)
    if ev.get("source") in ("compact", "resume") and d.exists():
        partes.append(f"[holmes] Fim do diário desta sessão (inteiro em {d.relative_to(H.RAIZ)}):\n"
                      + d.read_text(encoding="utf-8")[-2500:])
    return saida("SessionStart", "\n\n".join(partes))


def pistas(ev):
    prompt = ev.get("prompt", "")
    if len(H.C.termos(prompt)) < 3:
        return None
    try:
        caso = H.caso_ativo()
    except H.Erro:
        return None
    vistos_f = ESTADO / "sessoes" / f"{ev.get('session_id', 'x')}.vistos"
    vistos = set(vistos_f.read_text().split("\n")) if vistos_f.exists() else set()
    chave = lambda l: " ".join(l.split(" ", 2)[:2])  # "H12 [..." ou "corpus #37"
    linhas = [l for l in holmes("busca", prompt, "-n", "6").splitlines()
              if l and not l.startswith((" ", "(")) and chave(l) not in vistos][:6]
    with H.conecta(caso) as db:
        alerta = [f"⚠ túnel em F{f['id']} ({H.aviso_tunel(*t)}): leia antes de testar"
                  for f in db.execute("SELECT id FROM no WHERE tipo='frente' AND estado='ativa'").fetchall()
                  if (t := H.tunel(db, f["id"]))[0] >= H.TUNEL]
        lida = H.pede_leitura(db)
        if lida:
            alerta.append("⚠ " + lida)
    if not linhas and not alerta:
        return None
    vistos_f.parent.mkdir(parents=True, exist_ok=True)
    vistos_f.write_text("\n".join(vistos | {chave(l) for l in linhas}))
    corpo = "\n".join(alerta + linhas)[:1500]
    return saida("UserPromptSubmit", f"[holmes] O banco já tem sobre isto (detalhe: `holmes.py ver <id>`):\n{corpo}")


def guarda(ev):
    cmd = (ev.get("tool_input") or {}).get("command", "")
    if re.search(r"\bpkill\s+(-\w*\s+)*-\w*f", cmd):
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                "permissionDecisionReason": "[holmes] `pkill -f` casa com a linha do próprio shell e o mata. "
                                            "Mate por PID explícito (registrado no teste)."}}
    return None


def roda_script_do_caso(cmd):
    try:
        caso = H.caso_ativo()
    except H.Erro:
        return None, None
    m = SCRIPT.search(cmd)
    if m and not m[1].endswith(("holmes.py", "hooks.py")) and (f"casos/{caso}/" in cmd or "/scripts/" in m[1]):
        return caso, m[1]
    return None, None


def pos(ev):
    caso, script = roda_script_do_caso((ev.get("tool_input") or {}).get("command", ""))
    if not script:
        return None
    with H.conecta(caso) as db:
        ok = db.execute("SELECT 1 FROM teste t JOIN no n ON n.id=t.no WHERE n.estado IN ('planejado','rodando') "
                        "AND t.script LIKE ?", (f"%{Path(script).name}%",)).fetchone()
    if ok:
        return None
    return saida("PostToolUse", f"[holmes] {Path(script).name} rodou sem teste aberto que o cite. Se foi "
                 "exploração, tudo bem; se o resultado vai sustentar ou descartar algo, registre com "
                 "`holmes.py teste <H> ... --script` e `resultado`, com alcance, senão ele não vale como fechamento.")


def ultimo_turno(transcript):
    eventos, inteiro = cauda(transcript, 4 << 20)
    if not inteiro and not any(e.get("type") == "user" and not e.get("isMeta") for e in eventos):
        eventos = cauda(transcript, None)[0]  # turno maior que a cauda
    inicio = max((i for i, e in enumerate(eventos) if e.get("type") == "user" and not e.get("isMeta") and (
        isinstance((e.get("message") or {}).get("content"), str) or any(
            isinstance(b, dict) and b.get("type") == "text" for b in (e.get("message") or {}).get("content") or []))),
        default=0)
    return [b.get("input") or {} for e in eventos[inicio:] if e.get("type") == "assistant"
            for b in (e.get("message") or {}).get("content") or []
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Bash"]


def fim(ev):
    try:
        atualiza_diario(ev)
    except Exception as e:  # diário é bônus; nunca derruba o fim do turno
        print(f"[holmes] diário falhou: {e}", file=sys.stderr)
    if ev.get("stop_hook_active"):
        return None
    cmds = [i.get("command", "") for i in ultimo_turno(ev["transcript_path"])]
    rodou = next((s for c in cmds for _, s in [roda_script_do_caso(c)] if s), None)
    if rodou and not any("holmes.py" in c for c in cmds):
        return {"decision": "block", "reason":
                f"[holmes] {Path(rodou).name} rodou neste turno e nada foi registrado. Registre o que ele mostrou "
                "(`holmes.py resultado T.. ` ou `novo fato`/`novo fio`), ou diga em uma linha por que não há o que "
                "registrar. Se ainda está rodando, registre o PID e o log no teste."}
    return None


def pre_compact(ev):
    atualiza_diario(ev)
    return None


ACOES = {"abertura": abertura, "pistas": pistas, "guarda": guarda, "pos": pos, "fim": fim,
         "pre-compact": pre_compact}

def marca(acao, ok):
    """Prova de execução, não de configuração: quando cada hook rodou pela última vez (`holmes.py saude`)."""
    arq = ESTADO / "hooks.json"
    try:
        v = json.loads(arq.read_text()) if arq.exists() else {}
        v = v if isinstance(v, dict) else {}
        v[acao] = f"{H.agora()} {'ok' if ok else 'FALHOU'}"
        arq.parent.mkdir(exist_ok=True)
        arq.write_text(json.dumps(v, ensure_ascii=False))
    except (OSError, ValueError):
        pass  # o registro é diagnóstico; nunca derruba o hook


if __name__ == "__main__":
    try:
        r = ACOES[sys.argv[1]](json.load(sys.stdin))
        marca(sys.argv[1], True)
        if r:
            print(json.dumps(r, ensure_ascii=False))
    except Exception as e:
        marca(sys.argv[1], False)
        print(f"[holmes] hook {sys.argv[1:]} falhou: {e}", file=sys.stderr)
