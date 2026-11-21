"""Testes herméticos do holmes 2.0: cada teste roda numa raiz temporária (nunca toca um caso real).

    python3 -m pytest holmes/          ou     python3 -I holmes/test_holmes.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def roda(raiz, *args, ok=True, script="holmes.py", stdin=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("HOLMES_")}
    env.update(HOLMES_RAIZ=str(raiz), HOLMES_TUNEL="3", HOLMES_LEITURA="4", HOLMES_EMBED_URL="fake")
    r = subprocess.run([sys.executable, "-I", str(AQUI / script), *args], capture_output=True, text=True,
                       env=env, input=stdin)
    assert (r.returncode == 0) == ok, (args, r.stdout, r.stderr)
    return r.stdout + r.stderr


def caso():
    raiz = Path(tempfile.mkdtemp())
    roda(raiz, "init", "demo", "Descobrir quem escreveu a carta")
    return raiz


def test_arvore_limites_e_alvos():
    r = caso()
    assert "OBJETIVO O1" in roda(r, "mapa")
    assert roda(r, "novo", "alvo", "Datar o papel", "--pai", "O1").strip() == "A2"
    assert roda(r, "novo", "alvo", "Achar o autor", "--pai", "O1").strip() == "A3"
    roda(r, "liga", "A3", "depende", "A2")
    roda(r, "novo", "hipotese", "Sem frente", ok=False)
    roda(r, "novo", "frente", "x" * 200, "--pai", "A2", ok=False)
    roda(r, "ver", "H2", ok=False)                                       # prefixo errado é pego
    for i in range(5):
        roda(r, "novo", "frente", f"Frente {i}", "--pai", "A2")
    assert "frentes ativas" in roda(r, "novo", "frente", "Sexta", "--pai", "A2", ok=False)
    roda(r, "estado", "F4", "estacionada", ok=False)                    # exige motivo
    roda(r, "estado", "F4", "estacionada", "sem material por ora")
    roda(r, "novo", "frente", "Agora cabe", "--pai", "A2")
    roda(r, "estado", "A2", "resolvido", "T9", ok=False)                 # exige --solucao
    roda(r, "estado", "A2", "resolvido", "marca d'água", "--solucao", "papel de 1897", "--prova", "true")
    assert "DESBLOQUEADO" in roda(r, "mapa")
    assert "não executadas" in roda(r, "prova") and "OK   A2" in roda(r, "prova", "--executa")


def test_execucoes_validade_tunel():
    r = caso()
    roda(r, "novo", "frente", "Papel", "--pai", "O1")
    roda(r, "novo", "hipotese", "Papel de 1890", "--pai", "F2", "--prob", "0.6", "--refuta-se", "fibra moderna")
    juiz = r / "juiz.py"
    juiz.write_text("print(1)\n")
    assert roda(r, "instrumento", str(juiz), "juiz de datas", "--verificador", "true").startswith("I4")
    roda(r, "teste", "H3", "Marca", "--alcance", "fábricas 1880-1900", ok=False)          # sem --porque
    t = roda(r, "teste", "H3", "Marca d'água", "--alcance", "fábricas inglesas 1880-1900", "--porque",
             "positivo data o papel; negativo só fecha fábricas inglesas", "--instrumento", "I4",
             "--previsao", "casa com Whatman", "--controle", "folha de 1895 conhecida", "--controle-tipo", "real")
    assert t.startswith("T5") and "sem controle real" not in t
    assert roda(r, "roda", "T5", "--pid", "999999", "--log", "saidas/x.log").strip() == "X1"
    m = roda(r, "mapa")
    assert "pid 999999 MORTO" in m and "PID morto" in m
    roda(r, "resultado", "T5", "negativo", "nenhuma marca casa", "--controle-ok", "sim", "--n", "412",
         "--sentido", "nenhuma fábrica inglesa: o papel pode ser de outro país")
    assert "já existe T5" in roda(r, "teste", "H3", "Marca d'água", "--alcance", "fábricas inglesas 1880-1900",
                                  "--porque", "x", ok=False)
    v = roda(r, "ver", "T5")
    assert "previsão ANTES" in v and "n=412" in v
    juiz.write_text("print(2)\n")                                       # conserta o instrumento
    assert "1 negativo(s) ficam A REVALIDAR" in roda(r, "instrumento", str(juiz))
    assert "A REVALIDAR" in roda(r, "ja", "marca fábricas inglesas")
    assert roda(r, "roda", "T5").strip() == "X2"                        # re-execução com a versão nova
    out = roda(r, "resultado", "T5", "negativo", "de novo nada", "--controle-ok", "sim", "--sentido", "nenhum: a mesma ausência de antes")
    assert "A REVALIDAR" not in out
    for i in range(2):
        roda(r, "teste", "H3", f"Fibra {i}", "--alcance", f"amostra {i}", "--porque", "p")
        out = roda(r, "resultado", f"T{6 + i}", "negativo", "nada")
    assert "TÚNEL" in out and "INDETERMINADO" in out
    m = roda(r, "mapa")
    assert "TÚNEL em F2" in m and "2 negativo(s) sem instrumento" in m
    roda(r, "teste", "H3", "Controle quebrado", "--alcance", "a", "--porque", "p")
    assert "INVÁLIDO" in roda(r, "resultado", "T8", "positivo", "achou?", "--controle-ok", "nao")
    roda(r, "teste", "H3", "Selo seco", "--alcance", "b", "--porque", "p", "--instrumento", "I4",
         "--controle", "folha de 1895", "--controle-tipo", "real")
    assert "controle não confirmado" in roda(r, "resultado", "T9", "negativo", "nada")


def test_fatos_fontes_corpus_e_entidades():
    r = caso()
    doc = r / "casos/demo/fontes/carta.md"
    doc.write_text("Prezado senhor,\n\nA tinta ferrogálica escurece com o tempo.\n\nAssinado, M.")
    chat = r / "chat.json"
    chat.write_text(json.dumps({"messages": [
        {"id": i, "type": "message", "date": f"2020-01-0{i + 1}T10:00", "from": "ana", "text": t}
        for i, t in enumerate(["oi", "a fechadura tem três pinos", "fim"])]}))
    assert "indexado" in roda(r, "fonte", str(doc), "--confiabilidade", "B")
    assert "sem mudança" in roda(r, "fonte", str(doc))
    roda(r, "fonte", str(chat), "--procedencia", "terceiros")
    b = roda(r, "busca", "tinta ferrogalica")                           # sem acento casa
    assert "corpus #" in b
    pid = b.split("corpus #")[1].split(" ")[0]
    e = roda(r, "cita", pid, "A carta usa tinta ferrogálica").strip()
    assert e.startswith("E") and "conferida" in e
    eid = e.split()[0]
    v = roda(r, "ver", eid)
    assert "citacao: Prezado senhor" in v and "deriva" in v
    assert "não é fato" in roda(r, "novo", "fato", "Fulano disse que a carta é falsa", "--natureza", "relato", ok=False)
    roda(r, "novo", "pista", "Fulano disse que a carta é falsa", "--origem", "externo", "--natureza", "relato")
    assert "pista:aberta relato/externo/C" in roda(r, "busca", "fulano falsa", "--sem-corpus")
    assert "1 pista(s) aberta(s)" in roda(r, "mapa")
    assert "provado:fonte" in roda(r, "busca", "tinta ferrogalica", "--sem-corpus")
    roda(r, "novo", "fato", "Carta sem data", ok=False)                                     # fato sem prova não existe
    roda(r, "novo", "fato", "A carta foi escrita por um canhoto", "--natureza", "inferencia", "--por", "fonte",
         ok=False)                                                                              # inferência não é fato
    kinf = roda(r, "novo", "pista", "A carta foi escrita por um canhoto", "--natureza", "inferencia").strip()
    assert kinf.startswith("K")
    assert "não vira fato" in roda(r, "confere", kinf, "parece", "--por", "fonte", ok=False)
    kmed = roda(r, "novo", "pista", "A tinta reage ao ferro no teste de cor", "--natureza", "medicao").strip()
    roda(r, "confere", kmed, "refeito", "--por", "medicao", ok=False)                       # medição exige --prova
    assert "era a pista" in roda(r, "confere", kmed, "refeito", "--por", "medicao", "--prova", "true")
    assert "provado:medicao" in roda(r, "ver", kmed) or "medicao" in roda(r, "ver", kmed)
    assert "fato:vigente medicao" in roda(r, "busca", "reage ferro", "--sem-corpus")        # a pista virou fato
    assert roda(r, "ver", "E" + kmed[1:]).startswith("E")                                   # mesmo nó, prefixo novo
    roda(r, "novo", "fato", "Sem lastro", "--por", "fonte", ok=False)                       # fonte que aponta para nada
    assert "pista" in roda(r, "cita", pid, "O autor quis dizer X", "--natureza", "interpretacao", ok=False)
    kdesc = roda(r, "novo", "pista", "Talvez a tinta seja posterior", "--natureza", "observacao").strip()
    roda(r, "estado", kdesc, "descartada", "não há como datar a tinta")
    assert "provar não desfaz" in roda(r, "confere", kdesc, "relido", "--por", "fonte", ok=False)  # não ressuscita
    j = r / "ext.json"
    j.write_text('{"observacoes": [{"id": "o1", "texto": "Agente externo diz que a chave confere", '
                 '"origem": "externo", "por": "medicao", "prova": "true"}]}')
    assert "pista/observacao" in roda(r, "extrai", str(j))                                  # externo não se autoprova
    kfon = roda(r, "novo", "pista", "O papel tem marca d'água", "--natureza", "observacao").strip()
    roda(r, "confere", kfon, "ok", "--por", "fonte", ok=False)                             # nota não é localizador
    assert "provado por fonte" in roda(r, "confere", kfon, "vi contra a luz", "--por", "fonte", "--local", "folha 1")
    kte = roda(r, "novo", "pista", "A tinta é de 1897", "--natureza", "observacao").strip()
    assert "exige --prova" in roda(r, "confere", kte, "x", "--por", "teste", ok=False)
    # entidade com alias: buscar "lock" acha o que foi escrito como "fechadura"
    roda(r, "novo", "entidade", "fechadura", "--classe", "conceito", "--alias", "lock,tumbler")
    roda(r, "novo", "fio", "Medir os pinos da fechadura do porão")
    assert "Medir os pinos" in roda(r, "busca", "lock", "--sem-corpus")
    n = roda(r, "busca", "fechadura", "--sem-corpus").split("N")[1].split(" ")[0]
    roda(r, "atributo", f"N{n}", "pinos", "3", "--fato", eid)
    assert "pinos = 3" in roda(r, "ver", f"N{n}")
    assert "fechadura" in roda(r, "busca", "fechadura")                  # corpus de chat também aparece


def test_dependencias_contradicoes_ach_saude():
    r = caso()
    roda(r, "novo", "frente", "Autoria", "--pai", "O1")
    roda(r, "novo", "premissa", "A carta é de uma só pessoa", "--pai", "F2")       # R3
    roda(r, "novo", "hipotese", "Foi M.", "--pai", "F2", "--prob", "0.5")         # H4
    roda(r, "novo", "hipotese", "Foi o secretário", "--pai", "F2", "--prob", "0.3")  # H5
    roda(r, "liga", "H4", "depende", "R3")
    assert "premissas não verificadas: R3" in roda(r, "mapa")
    assert "dependem disto" in roda(r, "estado", "R3", "refutada", "duas caligrafias (E9)")
    assert "H4 depende de R3, que caiu" in roda(r, "mapa")
    roda(r, "novo", "fato", "Assinatura em tinta ferrogálica", "--estado", "vigente", "--por", "fonte", "--local", "folha 1")   # E6
    roda(r, "novo", "fato", "Assinatura em tinta de anilina", "--estado", "vigente", "--por", "fonte", "--local", "folha 1")    # E7
    roda(r, "liga", "E6", "contradiz", "E7")
    assert "contradição aberta: E6 × E7" in roda(r, "mapa")
    roda(r, "estado", "E7", "retratado", "li errado")
    assert "contradição aberta" not in roda(r, "mapa")
    assert "somam" not in roda(r, "prob", "H5", "0.3", "sem mudança")   # abaixo de 1 é a "outra"
    assert "se podem ser verdade juntas" in roda(r, "prob", "H5", "0.7", "coexistem?")
    roda(r, "prob", "H5", "0.3", "volta")
    roda(r, "ach", "E6", "H4", "C")
    roda(r, "ach", "E6", "H5", "II")
    m = roda(r, "ach", "F2")
    assert "sim" in m and "inconsist" in m
    s = roda(r, "saude")
    assert "sem critério de refutação" in s


def test_leitura_sentido_e_legado():
    r = caso()
    assert "LEITURA ATUAL: nenhuma" in roda(r, "mapa")
    roda(r, "novo", "frente", "Tinta", "--pai", "O1")                                # F2
    roda(r, "novo", "hipotese", "A tinta data a carta", "--pai", "F2")               # H3, sem critério
    assert "não diz o que a derrubaria" in roda(r, "teste", "H3", "Ferro", "--alcance", "a", "--porque", "p", ok=False)
    roda(r, "edita", "H3", "--refuta-se", "tinta moderna de anilina")
    roda(r, "teste", "H3", "Ferro", "--alcance", "a", "--porque", "p")               # T4
    assert "curto demais" in roda(r, "resultado", "T4", "negativo", "0 íons", "--sentido", "s", ok=False)
    out = roda(r, "resultado", "T4", "negativo", "0 íons", "--sentido", "sem ferro: talvez nem seja tinta antiga")
    assert "não o conceito inteiro" in out
    assert "sentido: sem ferro" in roda(r, "ver", "T4")
    assert "T4" in roda(r, "busca", "talvez antiga", "--sem-corpus")                # o sentido é pesquisável
    assert roda(r, "leitura", "A carta finge ser antiga; o papel e a tinta contam histórias diferentes.").startswith("L")
    m = roda(r, "mapa")
    assert "LEITURA ATUAL L" in m and "contam histórias diferentes" in m
    for i in range(4):
        roda(r, "teste", "H3", f"Forma {i}", "--alcance", f"a{i}", "--porque", "p")
        out = roda(r, "resultado", f"T{6 + i}", "inconclusivo", "?")
    assert "LEITURA DE CONJUNTO pendente: 4" in out and "LEITURA DE CONJUNTO" in roda(r, "mapa")
    assert "exige --motivo" in roda(r, "leitura", "Nova leitura: falsificação tardia.", ok=False)
    assert "substitui L5" in roda(r, "leitura", "Nova leitura: falsificação tardia.", "--motivo", "4 formas inconclusivas")
    assert "LEITURA DE CONJUNTO" not in roda(r, "mapa")
    assert "critério foi atingido: tinta moderna" in roda(r, "estado", "H3", "refutada", "T4")
    # herdado de outro sistema: a contradição sai dos alertas até alguém mexer num dos lados
    roda(r, "novo", "fato", "Tinta ferrogálica", "--estado", "vigente", "--por", "fonte", "--local", "folha 1")             # E11
    roda(r, "novo", "fato", "Tinta de anilina", "--estado", "vigente", "--por", "fonte", "--local", "folha 1")              # E12
    roda(r, "liga", "E11", "contradiz", "E12")
    import sqlite3
    with sqlite3.connect(r / "casos/demo/caso.db") as db:
        db.execute("UPDATE no SET legado=1")
    m = roda(r, "mapa")
    assert "contradição aberta" not in m and "herdado, fora dos alertas: 1 contradições" in m
    roda(r, "edita", "E11", "--resumo", "conferido de novo")
    assert "contradição aberta: E11 × E12" in roda(r, "mapa")


def test_corpus_modos():
    r = Path(tempfile.mkdtemp())
    (r / "a.md").write_text("Linha um\nD\nO\nO\nR\n\nA chave abre a porta do porão.")
    roda(r, "add", "docs", str(r / "a.md"), script="corpus.py")
    assert "porta" in roda(r, "busca", "chave porao", script="corpus.py")
    assert "#1" in roda(r, "busca", "D\nO\nO\nR", "--modo", "literal", script="corpus.py")   # padrão vertical cru
    assert "1 pedaços vetorizados" in roda(r, "embed", script="corpus.py")
    assert "porta" in roda(r, "busca", "porão", "--modo", "hibrido", script="corpus.py")


def test_hooks():
    r = caso()
    roda(r, "novo", "frente", "Tinta", "--pai", "O1")
    roda(r, "novo", "hipotese", "Tinta ferrogálica indica antes de 1900", "--pai", "F2")
    ab = json.loads(roda(r, "abertura", script="hooks.py", stdin=json.dumps({"source": "startup"})))
    assert "Caso ativo: demo" in ab["hookSpecificOutput"]["additionalContext"]
    ev = {"session_id": "s1", "prompt": "e a tinta ferrogálica, já vimos isso antes?"}
    assert "H3" in roda(r, "pistas", script="hooks.py", stdin=json.dumps(ev))
    assert roda(r, "pistas", script="hooks.py", stdin=json.dumps(ev)).strip() == ""   # não repete na sessão
    g = json.loads(roda(r, "guarda", script="hooks.py", stdin=json.dumps({"tool_input": {"command": "pkill -f sweep"}})))
    assert g["hookSpecificOutput"]["permissionDecision"] == "deny"
    cmd = "python3 casos/demo/scripts/varre.py"
    assert "rodou sem teste" in roda(r, "pos", script="hooks.py", stdin=json.dumps({"tool_input": {"command": cmd}}))
    tr = r / "t.jsonl"
    tr.write_text("\n".join(json.dumps(x) for x in [
        {"type": "user", "message": {"content": "rode o script"}, "timestamp": "2026-01-01T00:00"},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "rodando"},
                                                      {"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}}]))
    fim = json.loads(roda(r, "fim", script="hooks.py", stdin=json.dumps({"session_id": "s1", "transcript_path": str(tr)})))
    assert fim["decision"] == "block"
    assert "rode o script" in (r / ".holmes/diario/s1.md").read_text()
    tr.write_text("\n".join(json.dumps(x) for x in [                          # U+2028 não pode partir o evento
        {"type": "user", "message": {"content": "linha\u2028mesma mensagem"}, "timestamp": "2026-01-01T00:00"},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "ok\u2029fim"}]}}]))
    roda(r, "fim", script="hooks.py", stdin=json.dumps({"session_id": "s2", "transcript_path": str(tr)}))
    assert "mesma mensagem" in (r / ".holmes/diario/s2.md").read_text()
    vistos = roda(r, "saude").split("hooks vistos rodando:")[1]                  # execução vista, não configuração
    assert "abertura" in vistos and "fim" in vistos and "nunca vistos" not in vistos


def test_integridade_exploratorio_script_controle():
    r = caso()
    roda(r, "novo", "frente", "Papel", "--pai", "O1")
    roda(r, "novo", "hipotese", "Palpite: marca d'água holandesa", "--pai", "F2")                  # H3, sem critério
    roda(r, "teste", "H3", "Olhar contra a luz", "--alcance", "1 folha", "--porque", "p", ok=False)
    assert "exploratório" in roda(r, "teste", "H3", "Olhar contra a luz", "--alcance", "1 folha", "--porque", "p",
                                  "--exploratorio")                                                # T4
    assert "exploratório (vale como pista" in roda(r, "resultado", "T4", "positivo", "vi um leão",
                                                   "--sentido", "o leão é o brasão de Amsterdã")
    roda(r, "edita", "H3", "--refuta-se", "marca de outra cidade")
    juiz = r / "juiz.py"
    juiz.write_text("print(1)\n")
    roda(r, "instrumento", str(juiz), "juiz")                                                        # I5
    roda(r, "teste", "H3", "Catálogo", "--alcance", "c", "--porque", "p", "--instrumento", "I5", "--script",
         str(r / "sumiu.py"), "--controle", "folha conhecida", "--controle-tipo", "real")             # T6
    assert "não encontrado" in roda(r, "roda", "T6")
    assert "script não versionado" in roda(r, "resultado", "T6", "negativo", "nada", "--controle-ok", "sim")
    roda(r, "teste", "H3", "Lupa", "--alcance", "d", "--porque", "p", "--instrumento", "I5",
         "--controle", "folha conhecida", "--controle-tipo", "real")                                 # T7
    assert "controle não confirmado" in roda(r, "resultado", "T7", "positivo", "achou")              # positivo também
    k = roda(r, "novo", "pista", "A lupa mostra a marca", "--natureza", "observacao").strip()
    assert "não prova nada" in roda(r, "confere", k, "x", "--por", "teste", "--prova", "T7", ok=False)  # controle não visto
    roda(r, "resultado", "T7", "negativo", "x", "--sentido", "nenhum: x", ok=False)                  # motivo curto demais
    roda(r, "novo", "fato", "Prova vazia", "--prova", "", "--por", "fonte", "--local", "folha 1")
    assert "OK" not in roda(r, "prova", "--executa")                                                # vazio não prova nada


def test_extracao_conexao_e_leitura():
    """Percurso completo: material → observação → pista → conexão candidata → questão → hipótese → plano,
    com uma relação que não compartilha palavra (yin-yang ↔ duas metades)."""
    r = caso()
    roda(r, "novo", "frente", "Poema e desenho", "--pai", "O1")                                     # F2
    velho = roda(r, "novo", "fato", "O poema fala de duas metades que se buscam", "--estado", "vigente", "--por", "fonte", "--local", "folha 1").strip()
    q = roda(r, "novo", "questao", "O que o poema quer que se junte?", "--pai", "F2").strip()
    assert q.startswith("Q")
    assert "LACUNA: nenhuma hipótese" in roda(r, "questoes")
    assert f"formular explicações para {q}" in roda(r, "proximo")
    contrato = {
        "observacoes": [{"id": "o1", "texto": "O rodapé traz um símbolo yin-yang desenhado à mão",
                         "metodo": "inspeção visual da folha 2", "limites": "só a frente da folha"}],
        "pistas": [{"obs": "o1", "sobre": q, "porque": "símbolo isolado, fora do estilo do resto"}],
        "interpretacoes": [{"id": "i1", "sobre": "o1", "texto": "O símbolo pode marcar onde duas partes se completam",
                            "alternativas": "decoração; assinatura do desenhista"}],
        "hipoteses": [{"id": "h1", "texto": "As duas metades são as duas partes do mapa, que se completam",
                       "pai": "F2", "responde": q, "motivada_por": ["o1", velho], "prob": 0.3,
                       "refuta_se": "as partes do mapa não se encaixam por nenhuma borda", "rivais": ["h2"]},
                      {"id": "h2", "texto": "O símbolo é só decoração comum na época", "pai": "F2", "responde": q,
                       "prob": 0.4, "refuta_se": "o símbolo aparece em ponto estrutural do mapa"}],
        "conexoes": [{"de": "o1", "para": "h1", "relacao": "sustenta",
                      "porque": "yin-yang é a imagem clássica de duas metades complementares",
                      "rival": "símbolo popular, aparece em qualquer lugar", "discriminador": "o símbolo fica na junção das partes?"}],
        "discriminadores": [{"entre": ["h1", "h2"], "observacao": "posição do símbolo em relação às bordas do mapa"}],
        "impacto": {"leitura": "se h1 vingar, o caso é sobre reunir partes, não decifrar palavras"}}
    arq = r / "extracao.json"
    arq.write_text(json.dumps(contrato, ensure_ascii=False))
    import sqlite3
    conta = lambda: sqlite3.connect(r / "casos/demo/caso.db").execute("SELECT count(*) FROM no").fetchone()[0]
    antes = conta()
    plano = roda(r, "extrai", str(arq))
    assert "nada gravado" in plano and "pista/interpretação (não é fato)" in plano and conta() == antes
    ruim = dict(contrato, conexoes=contrato["conexoes"] + [{"de": "o1", "para": "E999", "relacao": "sobre", "porque": "x"}])
    (r / "ruim.json").write_text(json.dumps(ruim))
    roda(r, "extrai", str(r / "ruim.json"), "--aplica", ok=False)
    for i, ruim in enumerate(([], {"interpretacoes": [{"id": "i1"}]}, {"observacoes": [{"id": "H1", "texto": "x"}]},
                              {"observacoes": [{"id": "o1", "texto": "x", "pedaco": "abc"}]})):
        (r / f"r{i}.json").write_text(json.dumps(ruim))
        assert "Traceback" not in roda(r, "extrai", str(r / f"r{i}.json"), "--aplica", ok=False)
    assert conta() == antes                                                    # transação: nada ficou pela metade
    (r / "conf.json").write_text(json.dumps({"conexoes": [{"de": velho, "para": q, "relacao": "sobre", "porque": "x",
                                                           "estado": "confirmada"}]}))
    assert "só como 'sugerida'" in roda(r, "extrai", str(r / "conf.json"), "--aplica", ok=False)
    feito = roda(r, "extrai", str(arq), "--aplica")
    ids = dict(x.split("→") for x in feito.split("gravado: ")[1].strip().split(", "))
    o1, h1, h2, c1 = ids["o1"], ids["h1"], ids["h2"], ids["c1"]
    assert "mesmo texto já registrado" in roda(r, "extrai", str(arq))           # reaplicar não duplica
    v = roda(r, "ver", h1)
    assert f"~ conexão candidata {c1} [sugerida]" in v and "← sustenta" not in v   # candidata não é aresta
    assert "rival" in v and "responde" in v
    # descoberta: sem palavra comum o elo não aparece; com o conceito registrado como entidade, aparece
    assert velho not in roda(r, "conexoes", "símbolo yin-yang desenhado")      # controle: sem grafo nem conceito
    roda(r, "novo", "entidade", "complementaridade", "--classe", "conceito", "--alias", "duas metades,yin-yang")
    achou = roda(r, "conexoes", "símbolo yin-yang desenhado")
    assert velho in achou and "ponte" in achou and "'yin-yang' ↔ 'duas metades'" in achou and "nada foi gravado" in achou
    assert velho in roda(r, "conexoes", "metades complementares")               # texto livre com o conceito
    assert "termos em comum" not in roda(r, "conexoes", "o que é isto afinal")  # palavras vazias não ligam nada
    # promoção deliberada: só a confirmação cria a aresta
    roda(r, "estado", c1, "confirmada", ok=False)                               # exige motivo
    assert f"{o1} sustenta {h1}" in roda(r, "estado", c1, "confirmada", "símbolo está na junção (inspeção 2)")
    assert "← sustenta" in roda(r, "ver", h1)
    # teoria de trabalho ligada à evidência: se a base cai, a leitura aparece como dependente
    roda(r, "leitura", "O caso é sobre reunir duas partes, não decifrar palavras.", "--sustenta", f"{o1},{velho}",
         "--rival", h2, "--questao", q)
    m = roda(r, "mapa")
    assert ("base: " + ", ".join(sorted([o1, velho], key=lambda x: int(x[1:])))) in m and f"rivais: {h2}" in m and f"questão decisiva: {q}" in m and "PRÓXIMO" in m
    cai = roda(r, "estado", o1, "descartada", "o símbolo era mancha de tinta (lupa)")
    assert "L" in cai.split("reavaliados:")[1] and h1 in cai                    # transitivo: leitura e hipótese
    m = roda(r, "mapa")
    assert "que caiu" in m and "LEITURA DE CONJUNTO pedida por evento" in m
    assert "perdeu base" in roda(r, "proximo")
    assert "⚠ CAIU" in roda(r, "cadeia", h1)
    roda(r, "novo", "entidade", "Poema publicado", "--classe", "evento")
    n = roda(r, "busca", "poema publicado", "--sem-corpus").split("N")[1].split(" ")[0]
    roda(r, "atributo", f"N{n}", "quando", "1897-03-01", "--fato", velho)
    assert "1897-03-01" in roda(r, "cronologia")


def test_aval_sintetico():
    """O mecanismo de descoberta no caso de gabarito conhecido, e o avaliador de uma investigação."""
    out = roda(Path(tempfile.mkdtemp()), "recuperacao", script="aval/aval.py")
    assert "conexoes + conceitos   ligações 9/9 (não literais 7/7)" in out, out
    r = caso()
    g = json.loads((AQUI / "aval/relojoeiro.json").read_text(encoding="utf-8"))
    txt = {p["id"]: p["texto"] for p in g["pistas"]}
    e = {k: roda(r, "novo", "fato", txt[k], "--estado", "vigente", "--origem", "fonte", "--por", "fonte", "--local", "folha 1").strip() for k in ("c05", "c14", "c08")}
    c = roda(r, "conexao", e["c14"], e["c05"], "sustenta", "yin-yang e duas metades: complementaridade").split()[0]
    roda(r, "estado", c, "confirmada", "o símbolo está no rodapé do próprio poema")
    t = roda(r, "conexao", e["c08"], e["c05"], "sobre", "mesma expressão 'duas metades'", "--rival", "coincidência").split()[0]
    roda(r, "estado", t, "rejeitada", "canteiro não tem relação com o poema")
    p = json.loads(roda(r, "pontua", str(r / "casos/demo/caso.db"), script="aval/aval.py"))
    assert p["ligacoes_verdadeiras_no_grafo"] == "1/9" and p["armadilhas_aceitas_no_grafo (falso positivo)"] == 0
    assert p["armadilhas_rejeitadas_explicitamente"] == 1 and p["pistas_registradas"] == "3/30"


def test_ramos_passos_trilha_ficha():
    r = caso()
    roda(r, "novo", "alvo", "Datar o papel", "--pai", "O1")                       # A2
    roda(r, "estado", "A2", "resolvido", "marca d'água", "--solucao", "papel de 1897")
    roda(r, "novo", "alvo", "Achar o autor", "--pai", "O1")                       # A3
    roda(r, "novo", "questao", "Quem assina 'J.'?", "--pai", "A3")                 # Q4
    roda(r, "novo", "ramo", "x", "--pai", "Q4", ok=False)                          # ramo só via `ramo novo`
    roda(r, "ramo", "novo", "J. = John", "--de", "Q4", ok=False)                   # sem --porque
    assert roda(r, "ramo", "novo", "J. = John", "--de", "Q4", "--porque", "o carimbo diz John & Co").startswith("B5")
    assert roda(r, "novo", "fato", "Carimbo John & Co no verso", "--porque", "li o verso", "--por", "fonte", "--local", "folha 1").strip() == "E6"
    roda(r, "passo", "pensou", "John era sócio, não autor", ok=False)              # passo sem porquê
    roda(r, "passo", "pensou", "John era sócio, não autor", "--porque", "E6 é carimbo comercial")
    # volta ao passo 1 e abre outra direção: o galho herda só o que veio antes
    assert roda(r, "ramo", "novo", "J. = Jane", "--de", "B5", "--passo", "1", "--porque",
                "a letra é a mesma das cartas de Jane").startswith("B7")
    roda(r, "estado", "B5", "morto", ok=False)                                     # morrer exige motivo
    roda(r, "estado", "B5", "morto", "E6: John era só a firma")
    t = roda(r, "trilha", "B7")
    assert "Q4" in t and "1. abriu" in t and "porque: o carimbo diz John" in t
    assert "John era sócio" not in t                                               # passo 3 de B5 é posterior ao corte
    assert "a letra é a mesma" in t
    t5 = roda(r, "trilha", "B5")
    assert "registrou: E6" in t5 and "bifurcou: → B7" in t5 and "mudou: B5 ativo → morto" in t5
    a = roda(r, "arvore")
    assert "▶ B7 [ativo]" in a and "B5 [morto]" in a and "(do passo 1)" in a and "A2 [resolvido] Datar o papel ✓" in a
    roda(r, "passo", "proximo", "comparar a letra com 3 cartas de Jane", "--porque", "discrimina Jane de um copista")
    fi = roda(r, "ficha")
    assert "IMEDIATO B7" in fi and "PRÓXIMA EXPERIÊNCIA: comparar a letra" in fi
    assert "JÁ PERCORRIDO" in fi and "B5 [morto]" in fi and "John era só a firma" in fi and "papel de 1897" in fi
    assert "RAMO ATIVO B7" in roda(r, "mapa")
    roda(r, "estado", "B7", "pausado", "esperando as cartas")
    assert "RAMO ATIVO: nenhum" in roda(r, "mapa")
    assert "abriu: nasce de B5 (passo 1)" in roda(r, "ver", "B7")
    assert "B7" in roda(r, "busca", "copista")                                     # o passo é pesquisável
    roda(r, "estado", "B7", "ativo")                                                        # porquê longo não trava o ramo
    roda(r, "ramo", "usa", "B7")
    roda(r, "novo", "frente", "Letra", "--pai", "A3")
    h = roda(r, "novo", "hipotese", "Jane escreveu", "--pai", "F" + roda(r, "busca", "Letra", "--sem-corpus").split("F")[1].split(" ")[0],
             "--refuta-se", "letra diferente").strip()
    assert roda(r, "teste", h, "Letra igual?", "--alcance", "3 cartas", "--porque", "x" * 550).strip().startswith("T")


def test_reorganiza_banco_antigo():
    import sqlite3
    r = caso()
    roda(r, "novo", "fato", "Papel de 1897", "--por", "fonte", "--local", "folha 1")                    # E2, fora de ramo
    roda(r, "ramo", "novo", "Linha do papel", "--de", "O1", "--porque", "começar")  # B3
    roda(r, "passo", "pensou", "O papel data a carta", "--porque", "marca d'água", "--nos", "E2")
    db = sqlite3.connect(r / "casos" / "demo" / "caso.db")                          # banco de antes do modelo
    i = db.execute("INSERT INTO no(tipo, titulo, estado, origem, criado, atualizado) VALUES "
                   "('fato', 'Talvez a carta seja de um canhoto', 'vigente', 'agente', 'x', 'x')").lastrowid
    db.execute("INSERT INTO fato(no, natureza) VALUES (?, 'inferencia')", (i,)); db.commit(); db.close()
    assert "sem prova registrada" in roda(r, "mapa", "--tudo")                       # banco antigo: avisa
    plano = roda(r, "reorganiza")
    assert "viram pista 1 (inferencia 1)" in plano and "ganham ramo 1" in plano and "plano apenas" in plano
    assert roda(r, "ver", f"E{i}").startswith(f"E{i} [fato:vigente")              # nada gravado sem --aplica
    roda(r, "reorganiza", "--aplica")
    assert f"K{i} [pista:aberta inferencia" in roda(r, "busca", "canhoto", "--sem-corpus")
    assert "no ramo: B3" in roda(r, "ver", "E2")
    assert "viram pista 0" in roda(r, "reorganiza")                              # idempotente


def test_releitura_revalidacao_e_retomada():
    """plano.md §7 (releitura por contradição e por hipótese central), §16 (instrumento) e §14 (compactação)."""
    r = caso()
    roda(r, "novo", "frente", "F", "--pai", "O1")
    roda(r, "novo", "fato", "A", "--por", "fonte", "--local", "folha 1"); roda(r, "novo", "fato", "B", "--por", "fonte", "--local", "folha 1")   # E3 E4
    roda(r, "novo", "hipotese", "Central", "--pai", "F2", "--prob", "0.5", "--refuta-se", "r")              # H5
    roda(r, "leitura", "quadro", "--sustenta", "E3", "--rival", "H5")
    assert "rever a leitura de conjunto" not in roda(r, "proximo")
    roda(r, "liga", "E3", "contradiz", "E4")
    assert "contradição registrada" in roda(r, "proximo")
    roda(r, "prob", "H5", "0.1", "caiu")
    assert "hipótese central mudou de peso (H5 0.5→0.1)" in roda(r, "mapa")
    juiz = r / "j.py"
    juiz.write_text("print(1)\n")
    roda(r, "instrumento", str(juiz), "j")                                                                   # I7
    roda(r, "teste", "H5", "t", "--alcance", "a", "--porque", "p", "--instrumento", "I7", "--controle", "c",
         "--controle-tipo", "real")                                                                         # T8
    roda(r, "resultado", "T8", "negativo", "n", "--controle-ok", "sim")
    juiz.write_text("print(2)\n")
    roda(r, "instrumento", str(juiz))
    assert "rodar de novo T8 com o instrumento atual" in roda(r, "proximo")
    tr = r / "t.jsonl"
    tr.write_text(json.dumps({"type": "user", "message": {"content": "decidimos estacionar a frente F"},
                              "timestamp": "2026-01-01T00:00"}))
    roda(r, "pre-compact", script="hooks.py", stdin=json.dumps({"session_id": "s", "transcript_path": str(tr)}))
    ab = json.loads(roda(r, "abertura", script="hooks.py", stdin=json.dumps({"session_id": "s", "source": "compact"})))
    ctx = ab["hookSpecificOutput"]["additionalContext"]
    assert "estacionar a frente F" in ctx and "MAPA" in ctx and "LEITURA ATUAL" in ctx    # plano + teoria + diário


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_"):
            f()
            print("ok", nome)
