#!/usr/bin/env python3
"""holmes 2.0 — o raciocínio da investigação num grafo SQLite por caso (modelo em MODELO.md).

Árvore: objetivo O → alvo A → frente F → hipótese H / premissa R → teste T → execução X.
Ao lado: fato E (cita fonte S), entidade N, decisão do usuário D, fio P, instrumento I, questão Q,
conexão candidata C (relação sugerida, fora do grafo até ser confirmada), leitura L (teoria de trabalho).
O plano é a consulta `mapa`; o material bruto fica no corpus (holmes/corpus.py).

  caso       init <caso> "<objetivo>" · usa <caso> · casos
  plano      mapa [--tudo] · proximo · ver <id> · cadeia <id> · questoes · cronologia · saude
             busca "<txt>" [--sem-corpus] · ja "<txt>"
  leitura    leitura "<o quadro>" [--sustenta E,..] [--enfraquece E,..] [--rival H,..] [--questao Q]
                     [--lacuna Q,..] [--motivo "<por que mudou>"]          (sem texto: mostra a atual)
  relações   conexoes <id|"texto"> [-n 8]   (candidatas por consulta; nada é gravado)
             conexao <de> <para> <relação> "<por quê>" [--rival] [--discriminador] [--motivos E,..]
             estado C.. confirmada|rejeitada "<motivo>"   (confirmada vira aresta do grafo)
  extração   extrai <arquivo.json> [--aplica] [--so id,..] [--rejeita id,..]   (contrato em MODELO.md)
  criar      novo <tipo> "<título>" [--pai ID] [--resumo] [--origem] [--grau] [--estado]
             [--natureza --fonte S --local --citacao]   (fato)
             [--prob --refuta-se]                       (hipótese)
             [--classe --alias "a,b"]                   (entidade)
             [--proibe --permite]                       (decisão)
  mudar      estado <id> <estado> "<motivo>" [--solucao]  · edita <id> [--titulo] [--resumo] [--refuta-se]
             liga <de> <tipo> <para> ["nota"] · desliga <de> <tipo> <para>
             prob <H> <0..1> "<motivo>" · ach <E> <H> CC|C|N|I|II · ach <F>   (matriz)
  testar     teste <H> "<título>" --alcance .. --porque .. [--fora] [--previsao] [--controle --controle-tipo]
                   [--instrumento I] [--script] [--forca] [--exploratorio]
             roda <T> [--pid] [--log] [--host]  → X       resultado <T|X> positivo|negativo|inconclusivo|falhou
             "<nota>" [--sentido "<o que diz>"|"nenhum: <por quê>"|"revisar: <o quê>"] [--n ..] [--controle-ok]
             jobs
  fontes     fonte <arquivo|pasta|url> [--procedencia] [--confiabilidade A-F] [--sem-corpus]
             cita <pedaço do corpus> "<afirmação>" [--natureza] [--grau]   confere <E> "<nota>" --por fonte|medicao|teste|reproducao [--prova ..]
  entidades  atributo <N> <chave> <valor> [--fato E]
  provas     instrumento <caminho> "<nome>" [--verificador "cmd"] · prova [--executa] [--legado]
             (sem --executa só lista: são comandos de shell guardados no banco)

Ambiente: HOLMES_RAIZ, HOLMES_CASOS, HOLMES_CASO (força o caso), HOLMES_TUNEL (padrão 5), HOLMES_CORPUS,
HOLMES_LEITURA (padrão 6: resultados sem leitura de conjunto antes de o mapa pedir uma).
"""
import argparse
import hashlib
import os
import re
import socket
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus as C  # noqa: E402

RAIZ = Path(os.environ.get("HOLMES_RAIZ") or Path(__file__).resolve().parents[1])
CASOS = Path(os.environ.get("HOLMES_CASOS") or RAIZ / "casos")
ATIVO = RAIZ / ".holmes" / "ativo"
TUNEL = int(os.environ.get("HOLMES_TUNEL") or 5)
LEITURA_A_CADA = int(os.environ.get("HOLMES_LEITURA") or 6)
MAX_FRENTES, MAX_HIP, MAX_MAPA = 5, 7, 3500

PREFIXO = {"objetivo": "O", "alvo": "A", "frente": "F", "hipotese": "H", "premissa": "R", "teste": "T",
           "fato": "E", "entidade": "N", "decisao": "D", "fio": "P", "fonte": "S", "instrumento": "I",
           "leitura": "L", "questao": "Q", "conexao": "C", "ramo": "B", "pista": "K"}
TIPO_DE = {v: k for k, v in PREFIXO.items()}
ESTADOS = {  # o primeiro é o inicial
    "objetivo": ["aberto", "atingido", "abandonado"],
    "alvo": ["aberto", "resolvido", "bloqueado"],
    "frente": ["ativa", "estacionada", "fechada", "descartada"],
    "hipotese": ["viva", "apoiada", "refutada", "estacionada"],
    "premissa": ["assumida", "verificada", "refutada"],
    "teste": ["planejado", "rodando", "feito", "cancelado"],
    "fato": ["vigente", "contestado", "retratado"],  # fato é constatação já provada: nasce vigente
    "pista": ["aberta", "descartada"],  # o que ainda não está provado; provada, vira fato (`confere`)
    "entidade": ["ativa", "fundida"],
    "decisao": ["vigente", "revogada"],
    "fio": ["aberto", "fechado", "estacionado"],
    "fonte": ["catalogada", "indexada"],
    "instrumento": ["vigente", "obsoleto"],
    "leitura": ["vigente", "substituida"],
    "questao": ["aberta", "respondida", "reformulada", "estacionada"],
    "conexao": ["sugerida", "confirmada", "rejeitada"],
    "ramo": ["ativo", "pausado", "morto", "fundido", "concluido"],
}
COM_MOTIVO = {"atingido", "abandonado", "resolvido", "bloqueado", "estacionada", "fechada", "descartada",
              "refutada", "verificada", "cancelado", "contestado", "retratado", "fundida", "revogada", "fechado",
              "estacionado", "obsoleto", "respondida", "reformulada", "confirmada", "rejeitada", "pausado", "morto",
              "fundido", "concluido"}
CAIDOS = {"refutada", "retratado", "contestado", "descartada", "revogada", "abandonado", "cancelado", "rejeitada", "morto"}
VIVOS = {"aberto", "ativa", "viva", "apoiada", "assumida", "verificada", "planejado", "rodando", "feito",
         "rascunho", "vigente", "bloqueado", "resolvido", "aberta", "respondida", "sugerida", "confirmada", "ativo",
         "pausado"}
PAIS = {"alvo": {"objetivo", "alvo"}, "frente": {"alvo", "objetivo"}, "hipotese": {"frente"},
        "premissa": {"frente", "alvo", "objetivo"}, "teste": {"hipotese"},
        "questao": {"objetivo", "alvo", "frente", "questao"}}
ORIGENS = ["autor", "fonte", "medido", "usuario", "agente", "externo"]
NATUREZAS = ["observacao", "medicao", "citacao", "inferencia", "interpretacao", "relato"]
NATUREZAS_FATO = ["observacao", "medicao", "citacao"]  # inferência, interpretação e relato são pista
# responde: hipótese → questão que ela tenta responder · rival: explicação concorrente (leitura/hipótese → hipótese)
ARESTAS = ["sustenta", "enfraquece", "contradiz", "refuta", "depende", "duplica", "substitui", "sobre", "deriva",
           "responde", "rival"]
# passo: o "commit" de um ramo. Os manuais exigem --porque; registrou/mudou/abriu/bifurcou são automáticos.
PASSOS_MANUAIS = ["leu", "pensou", "testou", "achou", "corrigiu", "decidiu", "proximo"]
# como um fato vira provado: fato é constatação, e a prova pode não ser uma fonte
PROVAS = ["fonte", "medicao", "teste", "reproducao"]
ACH = {"CC": 2, "C": 1, "N": 0, "I": -1, "II": -2}

ESQUEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS no(id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL,
  pai INTEGER REFERENCES no(id), titulo TEXT NOT NULL CHECK(length(titulo) <= 160),
  resumo TEXT CHECK(length(resumo) <= 800), estado TEXT NOT NULL, origem TEXT, grau TEXT CHECK(grau IN ('A','B','C')),
  criado TEXT NOT NULL, atualizado TEXT NOT NULL, legado INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS no_pai ON no(pai, tipo, estado);
CREATE TABLE IF NOT EXISTS alvo(no INTEGER PRIMARY KEY REFERENCES no(id), solucao TEXT, prova TEXT);
CREATE TABLE IF NOT EXISTS hipotese(no INTEGER PRIMARY KEY REFERENCES no(id), prob REAL CHECK(prob BETWEEN 0 AND 1),
  refuta_se TEXT);
CREATE TABLE IF NOT EXISTS teste(no INTEGER PRIMARY KEY REFERENCES no(id),
  alcance TEXT NOT NULL CHECK(length(alcance) <= 600), fora TEXT CHECK(length(fora) <= 600),
  porque TEXT NOT NULL CHECK(length(porque) <= 600), previsao TEXT, previsao_em TEXT, controle TEXT,
  controle_tipo TEXT CHECK(controle_tipo IN ('real','plantado','sabotagem','nenhum')),
  instrumento INTEGER REFERENCES no(id), script TEXT, receita TEXT);
CREATE TABLE IF NOT EXISTS execucao(id INTEGER PRIMARY KEY, teste INTEGER NOT NULL REFERENCES no(id),
  versao INTEGER REFERENCES versao(id), script_sha TEXT, host TEXT, pid INTEGER, log TEXT, inicio TEXT, fim TEXT,
  n TEXT, controle_ok INTEGER, resultado TEXT CHECK(resultado IN ('positivo','negativo','inconclusivo','falhou')),
  nota TEXT, sentido TEXT);
CREATE TABLE IF NOT EXISTS instrumento(no INTEGER PRIMARY KEY REFERENCES no(id), caminho TEXT UNIQUE, verificador TEXT);
CREATE TABLE IF NOT EXISTS versao(id INTEGER PRIMARY KEY, instrumento INTEGER NOT NULL REFERENCES no(id),
  sha TEXT NOT NULL, quando TEXT NOT NULL, verificado INTEGER, nota TEXT);
CREATE TABLE IF NOT EXISTS fato(no INTEGER PRIMARY KEY REFERENCES no(id), natureza TEXT, fonte INTEGER REFERENCES no(id),
  local TEXT, citacao TEXT CHECK(length(citacao) <= 1000), conferido TEXT, prova TEXT);
CREATE TABLE IF NOT EXISTS fonte(no INTEGER PRIMARY KEY REFERENCES no(id), ref TEXT UNIQUE, sha TEXT,
  procedencia TEXT CHECK(procedencia IN ('primaria','derivada','terceiros','nossa')),
  confiabilidade TEXT CHECK(confiabilidade IN ('A','B','C','D','E','F')), documento INTEGER);
CREATE TABLE IF NOT EXISTS entidade(no INTEGER PRIMARY KEY REFERENCES no(id), classe TEXT, aliases TEXT);
CREATE TABLE IF NOT EXISTS atributo(entidade INTEGER REFERENCES no(id), chave TEXT, valor TEXT,
  fato INTEGER REFERENCES no(id), quando TEXT, PRIMARY KEY(entidade, chave));
CREATE TABLE IF NOT EXISTS decisao(no INTEGER PRIMARY KEY REFERENCES no(id), proibe TEXT, permite TEXT);
CREATE TABLE IF NOT EXISTS aresta(de INTEGER NOT NULL REFERENCES no(id), tipo TEXT NOT NULL,
  para INTEGER NOT NULL REFERENCES no(id), nota TEXT CHECK(length(nota) <= 200), criado TEXT, PRIMARY KEY(de, tipo, para));
CREATE TABLE IF NOT EXISTS ach(fato INTEGER REFERENCES no(id), hipotese INTEGER REFERENCES no(id), valor TEXT NOT NULL,
  nota TEXT, PRIMARY KEY(fato, hipotese));
CREATE TABLE IF NOT EXISTS legado(ref TEXT PRIMARY KEY, no INTEGER NOT NULL REFERENCES no(id));
CREATE TABLE IF NOT EXISTS conexao(no INTEGER PRIMARY KEY REFERENCES no(id), de INTEGER NOT NULL REFERENCES no(id),
  para INTEGER NOT NULL REFERENCES no(id), relacao TEXT NOT NULL, rival TEXT CHECK(length(rival) <= 400),
  discriminador TEXT CHECK(length(discriminador) <= 400), canal TEXT);
CREATE TABLE IF NOT EXISTS evento(id INTEGER PRIMARY KEY, no INTEGER, acao TEXT NOT NULL, texto TEXT, quando TEXT NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS idx USING fts5(ref UNINDEXED, texto, tokenize='unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS ramo(no INTEGER PRIMARY KEY REFERENCES no(id), de_passo INTEGER REFERENCES passo(id));
CREATE TABLE IF NOT EXISTS passo(id INTEGER PRIMARY KEY, ramo INTEGER NOT NULL REFERENCES no(id), tipo TEXT NOT NULL,
  texto TEXT NOT NULL CHECK(length(texto) <= 400), porque TEXT CHECK(length(porque) <= 400), nos TEXT,
  quando TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS passo_ramo ON passo(ramo, id);
"""


class Erro(Exception):
    pass


def agora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def casos():
    return sorted(p.parent.name for p in CASOS.glob("*/caso.db"))


def caso_ativo():
    c = os.environ.get("HOLMES_CASO") or (ATIVO.read_text().strip() if ATIVO.exists() else "")
    if not c:
        raise Erro("nenhum caso ativo: `holmes.py usa <caso>` (ou `init`)")
    if not (CASOS / c / "caso.db").exists():
        raise Erro(f"caso {c!r} não existe em {CASOS}")
    return c


def conecta(caso=None):
    db = sqlite3.connect(CASOS / (caso or caso_ativo()) / "caso.db", timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript(ESQUEMA)
    for tab, col, tipo in (("no", "legado", "INTEGER NOT NULL DEFAULT 0"), ("execucao", "sentido", "TEXT"),
                           ("teste", "modo", "TEXT"), ("no", "ramo", "INTEGER"), ("fato", "conferido_por", "TEXT")):
        if col not in {r[1] for r in db.execute(f"PRAGMA table_info({tab})")}:  # banco criado antes da coluna
            db.execute(f"ALTER TABLE {tab} ADD COLUMN {col} {tipo}")
    return db


def q(db, sql, *a):
    return db.execute(sql, a).fetchall()


def um(db, sql, *a):
    return db.execute(sql, a).fetchone()


def rot(r):
    return f"{PREFIXO[r['tipo']]}{r['id']}"


def pega(db, ref, tipo=None):
    if ":" in str(ref):  # id de outro sistema (ex.: ext:42), gravado ao importar
        l = um(db, "SELECT no FROM legado WHERE ref=?", str(ref).strip())
        if not l:
            raise Erro(f"{ref} não está no mapa de ids legados")
        ref = str(l["no"])
    m = re.fullmatch(r"([A-Z]?)(\d+)", str(ref).strip())
    if not m:
        raise Erro(f"id inválido: {ref!r} (use H12, T30…)")
    r = um(db, "SELECT * FROM no WHERE id=?", int(m[2]))
    if not r:
        raise Erro(f"{ref} não existe")
    if m[1] and PREFIXO[r["tipo"]] != m[1] and {m[1], PREFIXO[r["tipo"]]} != {"E", "K"}:
        raise Erro(f"{ref}: o nó {r['id']} é {r['tipo']} ({rot(r)}), não {TIPO_DE.get(m[1], m[1])}")
    if tipo and r["tipo"] not in ({tipo} if isinstance(tipo, str) else tipo):
        raise Erro(f"{ref} é {r['tipo']}, esperado {tipo}")
    return r


def evento(db, no, acao, texto=""):
    db.execute("INSERT INTO evento(no, acao, texto, quando) VALUES (?,?,?,?)", (no, acao, (texto or "")[:300], agora()))


def arq_ramo(caso):
    return RAIZ / ".holmes" / f"ramo-{caso}"


def ramo_ativo(db, caso):
    f = arq_ramo(caso)
    if not f.exists():
        return None
    try:
        r = um(db, "SELECT * FROM no WHERE id=? AND tipo='ramo'", int(f.read_text().strip()))
    except ValueError:
        return None
    return r if r and r["estado"] == "ativo" else None


ATUAL = {"ramo": None}  # ramo ativo desta invocação: cria(), estado e resultado gravam passos nele


def passo(db, ramo, tipo, texto, porque=None, nos=()):
    if porque and len(porque) > 400:
        raise Erro(f"--porque com {len(porque)} caracteres (máx. 400): o porquê do passo, não o dossiê")
    pid = db.execute("INSERT INTO passo(ramo, tipo, texto, porque, nos, quando) VALUES (?,?,?,?,?,?)",
                     (ramo, tipo, texto[:400], porque or None, ",".join(nos) or None, agora())).lastrowid
    db.execute("UPDATE no SET atualizado=? WHERE id=?", (agora(), ramo))
    indexa(db, ramo)
    return pid


def indexa(db, no):
    r = um(db, "SELECT * FROM no WHERE id=?", no)
    partes = [r["titulo"], r["resumo"] or ""] + [x["ref"] for x in q(db, "SELECT ref FROM legado WHERE no=?", no)]
    for sql in ("SELECT alcance, fora, porque, previsao FROM teste WHERE no=?",
                "SELECT citacao, local FROM fato WHERE no=?", "SELECT classe, aliases FROM entidade WHERE no=?",
                "SELECT proibe, permite FROM decisao WHERE no=?", "SELECT refuta_se FROM hipotese WHERE no=?",
                "SELECT solucao FROM alvo WHERE no=?", "SELECT nota, sentido FROM execucao WHERE teste=?",
                "SELECT chave || ' ' || valor FROM atributo WHERE entidade=?",
                "SELECT relacao, rival, discriminador FROM conexao WHERE no=?"):
        for x in q(db, sql, no):
            partes += [str(v) for v in x if v]
    if r["tipo"] == "ramo":  # o percurso é pesquisável: "como foi resolvido X?" acha o ramo pelos passos
        partes += [f"{p['texto']} {p['porque'] or ''}" for p in q(db, "SELECT texto, porque FROM passo WHERE ramo=?", no)]
    db.execute("DELETE FROM idx WHERE ref=?", (str(no),))
    db.execute("INSERT INTO idx(ref, texto) VALUES (?,?)", (str(no), " ".join(partes)))


def toca(db, no, acao, texto=""):
    # mexer num item herdado o traz para o presente: volta a entrar nos alertas do mapa
    db.execute("UPDATE no SET atualizado=?, legado=0 WHERE id=?", (agora(), no))
    evento(db, no, acao, texto)
    indexa(db, no)


# ---------- criar ----------

def prova_de(db, por, prova):
    """Fato é constatação provada: diz como (fonte, medição, teste, reprodução) e com o quê."""
    if por not in PROVAS:
        raise Erro("fato exige --por fonte|medicao|teste|reproducao: como ele está provado. "
                   "Sem prova ainda, é pista (`novo pista`)")
    if por in ("medicao", "reproducao") and not (prova or "").strip():
        raise Erro(f"--por {por} exige --prova \"<comando ou registro que reproduz a constatação>\"")
    if por == "teste":
        t = pega(db, prova or "", "teste")
        if not resultado_de(db, t["id"]):
            raise Erro(f"{rot(t)} não tem resultado registrado: um teste só prova depois de rodar")
        prova = rot(t)
    return por, prova


def cria(db, tipo, titulo, pai=None, resumo=None, origem=None, grau=None, estado=None, forca=False, **x):
    if tipo not in ESTADOS:
        raise Erro(f"tipo inválido {tipo!r}; use: {', '.join(ESTADOS)}")
    if len(titulo) > 160:
        raise Erro(f"título com {len(titulo)} caracteres (máx. 160): o detalhe vai em --resumo")
    if resumo and len(resumo) > 800:
        raise Erro(f"resumo com {len(resumo)} caracteres (máx. 800): uma conclusão por item; material vai ao corpus")
    if origem and origem not in ORIGENS:
        raise Erro(f"origem inválida; use: {', '.join(ORIGENS)}")
    p = pega(db, pai) if pai else None
    if tipo in PAIS and (not p or p["tipo"] not in PAIS[tipo]):
        raise Erro(f"{tipo} precisa de --pai do tipo {' ou '.join(sorted(PAIS[tipo]))}")
    if tipo == "ramo" and not p:
        raise Erro("ramo precisa de --de: o ponto (questão, hipótese, alvo, ramo…) de onde ele nasce")
    if tipo == "objetivo" and um(db, "SELECT 1 FROM no WHERE tipo='objetivo'"):
        raise Erro("o caso já tem objetivo (um só); sub-problemas são alvos")
    if tipo == "frente" and (estado or "ativa") == "ativa" and not forca:
        n = um(db, "SELECT count(*) FROM no WHERE tipo='frente' AND estado='ativa'")[0]
        if n >= MAX_FRENTES:
            raise Erro(f"já há {n} frentes ativas (máx. {MAX_FRENTES}): estacione ou feche uma antes")
    if tipo == "hipotese" and not forca:
        n = um(db, "SELECT count(*) FROM no WHERE tipo='hipotese' AND estado='viva' AND pai=?", p["id"])[0]
        if n >= MAX_HIP:
            raise Erro(f"{rot(p)} já tem {n} hipóteses vivas (máx. {MAX_HIP}): refute ou estacione uma")
    if origem == "externo" and not grau:
        grau = "C"  # subagente, outra IA, comunidade: grau C até ser provado (`confere --por`)
    estado = estado or ESTADOS[tipo][0]
    if estado not in ESTADOS[tipo]:
        raise Erro(f"estado {estado!r} inválido para {tipo}; use: {', '.join(ESTADOS[tipo])}")
    t = agora()
    no = db.execute("INSERT INTO no(tipo, pai, titulo, resumo, estado, origem, grau, criado, atualizado) "
                    "VALUES (?,?,?,?,?,?,?,?,?)", (tipo, p["id"] if p else None, titulo, resumo, estado,
                                                   origem or "agente", grau, t, t)).lastrowid
    if tipo in ("fato", "pista"):
        nat = x.get("natureza") or "observacao"
        if nat not in NATUREZAS:
            raise Erro(f"natureza inválida; use: {', '.join(NATUREZAS)}")
        por, prova = None, x.get("prova")
        if tipo == "fato":
            if nat not in NATUREZAS_FATO:
                raise Erro(f"{nat} não é fato: fato é constatação provada. Registre como pista "
                           f"(`novo pista \"..\" --natureza {nat}`) ou, se for explicação testável, como hipótese")
            por, prova = prova_de(db, x.get("por"), prova)
        fonte = pega(db, x["fonte"], "fonte")["id"] if x.get("fonte") else None
        db.execute("INSERT INTO fato(no, natureza, fonte, local, citacao, prova, conferido, conferido_por) "
                   "VALUES (?,?,?,?,?,?,?,?)", (no, nat, fonte, x.get("local"), x.get("citacao"), prova,
                                                t if por else None, por))
        if fonte:
            db.execute("INSERT OR IGNORE INTO aresta VALUES (?,?,?,?,?)", (no, "deriva", fonte, None, t))
    elif tipo == "hipotese":
        prob = x.get("prob")
        db.execute("INSERT INTO hipotese VALUES (?,?,?)", (no, prob, x.get("refuta_se")))
    elif tipo == "entidade":
        db.execute("INSERT INTO entidade VALUES (?,?,?)", (no, x.get("classe"), x.get("alias")))
    elif tipo == "decisao":
        db.execute("INSERT INTO decisao VALUES (?,?,?)", (no, x.get("proibe"), x.get("permite")))
    elif tipo == "alvo":
        db.execute("INSERT INTO alvo(no) VALUES (?)", (no,))
    elif tipo == "ramo":
        db.execute("INSERT INTO ramo VALUES (?,?)", (no, x.get("de_passo")))
    rm = ATUAL["ramo"]
    if rm and tipo not in ("ramo", "objetivo", "fonte", "instrumento"):  # todo achado nasce dentro de uma linha
        db.execute("UPDATE no SET ramo=? WHERE id=?", (rm, no))
        passo(db, rm, "registrou", f"{PREFIXO[tipo]}{no} {titulo}", x.get("porque"), (f"{PREFIXO[tipo]}{no}",))
    evento(db, no, "criou", f"{tipo}: {titulo}")
    indexa(db, no)
    return no


# ---------- testes e execuções ----------

def sha_arquivo(c):
    p = Path(c)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def versao_atual(db, inst):
    return um(db, "SELECT * FROM versao WHERE instrumento=? ORDER BY id DESC LIMIT 1", inst)


def ultima(db, teste):
    """Última execução com resultado válido (falhou não conta)."""
    return um(db, "SELECT * FROM execucao WHERE teste=? AND resultado IS NOT NULL AND resultado != 'falhou' "
                  "ORDER BY id DESC LIMIT 1", teste)


def validade(db, teste):
    """Selo de validade do resultado de um teste. Vazio = a conclusão está autorizada no alcance declarado.
    Separa quatro coisas: a execução aconteceu; o resultado foi observado; o controle passou (visto, não
    declarado); a conclusão é autorizada (instrumento atual, script versionado, teste confirmatório)."""
    x = ultima(db, teste)
    if not x:
        return ""
    t = um(db, "SELECT * FROM teste WHERE no=?", teste)
    if x["controle_ok"] == 0:
        return "INVÁLIDO (controle falhou)"
    if t["modo"] == "exploratorio":
        return "exploratório (vale como pista; não fecha nem confirma)"
    if x["resultado"] not in ("negativo", "positivo"):
        return ""
    if x["resultado"] == "negativo" and not x["versao"]:
        return "INDETERMINADO (sem instrumento)"
    atual = versao_atual(db, t["instrumento"]) if t["instrumento"] else None
    if x["resultado"] == "negativo" and atual and atual["id"] != x["versao"]:
        return "A REVALIDAR (instrumento mudou)"
    if t["script"] and not x["script_sha"]:
        return "script não versionado (arquivo ausente ao rodar)"
    if t["controle_tipo"] in (None, "nenhum", "plantado"):
        return "sem controle real"
    if x["controle_ok"] is None:  # declarar controle real não é o mesmo que vê-lo passar
        return "controle não confirmado (--controle-ok)"
    return ""


def resultado_de(db, teste):
    x = ultima(db, teste)
    return x["resultado"] if x else None


def tunel(db, frente):
    """(negativos seguidos, quantos deles válidos). O primeiro número mede estagnação: tentativa indeterminada
    também é esforço sem avanço. O segundo é o que pode sustentar conclusão (instrumento e controle vistos)."""
    hs = q(db, "SELECT id, criado FROM no WHERE tipo='hipotese' AND pai=?", frente)
    if not hs:
        return 0, 0
    data = lambda t: (t or "")[:19].replace("T", " ")  # herdado grava '2026-11-20T03:30:26Z'; agora() usa espaço
    marco = max(data(h["criado"]) for h in hs)
    ex = q(db, f"SELECT x.*, tt.modo FROM execucao x JOIN no t ON t.id=x.teste JOIN teste tt ON tt.no=x.teste "
               f"WHERE t.pai IN ({','.join('?' * len(hs))}) AND x.resultado IS NOT NULL AND x.resultado != 'falhou'",
           *[h["id"] for h in hs])
    n = validos = 0
    for x in sorted(ex, key=lambda x: (data(x["fim"]), x["id"])):
        if x["resultado"] != "negativo":
            n, validos, marco = 0, 0, max(marco, data(x["fim"]))
        elif x["controle_ok"] != 0 and data(x["fim"]) >= marco:
            n += 1
            validos += bool(x["versao"]) and x["controle_ok"] == 1 and x["modo"] != "exploratorio"
    return n, validos


def aviso_tunel(n, validos):
    return (f"{n} negativos seguidos sem hipótese nova ({validos} com instrumento e controle vistos; "
            "os outros não fecham nada, mas contam como esforço sem avanço)")


def leitura_atual(db):
    return um(db, "SELECT * FROM no WHERE tipo='leitura' AND estado='vigente' ORDER BY id DESC LIMIT 1")


def base_leitura(db, lt):
    """A teoria de trabalho ligada ao registro: o que a sustenta, o que a enfraquece, as rivais, a questão
    decisiva e as lacunas. Se uma base cai, a leitura aparece em 'dependem de algo que caiu'."""
    partes = []
    for nome, sql in (("base", "SELECT para i FROM aresta WHERE de=? AND tipo='depende'"),
                      ("contra", "SELECT de i FROM aresta WHERE para=? AND tipo='enfraquece'"),
                      ("rivais", "SELECT para i FROM aresta WHERE de=? AND tipo='rival'"),
                      ("questão decisiva", "SELECT para i FROM aresta WHERE de=? AND tipo='sobre' AND nota='decisiva'"),
                      ("lacunas", "SELECT para i FROM aresta WHERE de=? AND tipo='sobre' AND nota='lacuna'")):
        rs = [um(db, "SELECT * FROM no WHERE id=?", x["i"]) for x in q(db, sql, lt["id"])]
        if rs:
            partes.append(f"{nome}: " + ", ".join(rot(r) + ("✗" if r["estado"] in CAIDOS else "") for r in rs))
    m = um(db, "SELECT nota FROM aresta WHERE de=? AND tipo='substitui'", lt["id"])
    if m and m["nota"]:
        partes.append(f"mudou porque: {m['nota'][:120]}")
    return " · ".join(partes)


def resultados_sem_leitura(db):
    """Resultados registrados depois da leitura de conjunto vigente (ou todos, sem leitura)."""
    l = leitura_atual(db)
    return um(db, "SELECT count(*) FROM execucao WHERE resultado IS NOT NULL AND resultado != 'falhou' "
                  "AND replace(substr(fim, 1, 19), 'T', ' ') > ?", l["criado"] if l else "")[0]


RELEVANTES = (("% positivo", "resultado positivo"), ("%→confirmada", "conexão confirmada"),
              ("%→respondida", "questão respondida"), ("%→reformulada", "questão reformulada"),
              ("%→refutada", "hipótese ou premissa refutada"), ("%→apoiada", "hipótese apoiada"),
              ("%→retratado", "fato retratado"), ("%→contestado", "fato contestado"),
              ("%→descartada", "pista ou frente descartada"), ("provado por %", "pista ou fato provado"),
              ("liga contradiz", "contradição registrada"))


def eventos_relevantes(db):
    """O que aconteceu desde a leitura vigente que pode mudar o quadro (não só quantos testes rodaram)."""
    l = leitura_atual(db)
    # pelo id do evento de criação, não pelo relógio: eventos no mesmo segundo da leitura não se perdem
    desde = um(db, "SELECT max(id) FROM evento WHERE no=? AND acao='criou'", l["id"])[0] if l else 0
    achados = []
    for padrao, nome in RELEVANTES:
        rs = q(db, "SELECT e.no FROM evento e JOIN no n ON n.id=e.no WHERE e.id > ? AND e.acao LIKE ? "
                   "AND n.legado=0 ORDER BY e.id", desde or 0, padrao)
        if rs:
            achados.append(f"{len(rs)} {nome} ({', '.join(rot(um(db, 'SELECT * FROM no WHERE id=?', r['no'])) for r in rs[:3])})")
    if l:  # hipótese central (ligada à leitura) mudou de peso em ≥ 0,2: o quadro pode ter mudado
        centrais = {x[0] for x in q(db, "SELECT para FROM aresta WHERE de=? AND tipo IN ('rival','depende') UNION "
                                        "SELECT a.de FROM aresta a JOIN aresta s ON s.para=a.para WHERE s.de=? AND "
                                        "s.tipo='sobre' AND a.tipo='responde'", l["id"], l["id"])}
        mudou = []
        for e in q(db, "SELECT no, acao FROM evento WHERE id > ? AND acao LIKE 'prob %'", desde or 0):
            m = re.fullmatch(r"prob (\S+)→(\S+)", e["acao"])
            if e["no"] in centrais and m and m[1] != "None" and abs(float(m[2]) - float(m[1])) >= 0.2:
                mudou.append(f"H{e['no']} {m[1]}→{m[2]}")
        if mudou:
            achados.append("hipótese central mudou de peso (" + ", ".join(mudou[:3]) + ")")
    return achados


def pede_leitura(db):
    """Revisão da teoria de trabalho motivada por evento; a contagem de resultados é só um lembrete."""
    ev = eventos_relevantes(db)
    if ev:
        return ("LEITURA DE CONJUNTO pedida por evento: " + "; ".join(ev) + ". Isso muda o que o caso parece "
                "contar? Se mudou, `holmes.py leitura \"...\" --sustenta .. --motivo ..`; se não, diga por quê.")
    n = resultados_sem_leitura(db)
    if n < LEITURA_A_CADA:
        return ""
    l = leitura_atual(db)
    pend = um(db, "SELECT count(*) FROM execucao x JOIN no t ON t.id=x.teste WHERE x.resultado IS NOT NULL AND "
                  "x.resultado != 'falhou' AND t.legado=0 AND (x.sentido IS NULL OR x.sentido LIKE 'revisar:%') AND "
                  "replace(substr(x.fim, 1, 19), 'T', ' ') > ?", l["criado"] if l else "")[0]
    return (f"LEITURA DE CONJUNTO pendente: {n} resultados desde a última" + (f" ({pend} com sentido pendente)" if pend else "")
            + ". Leia-os juntos (skill `leitura`): somados, mudam o quadro? Atualize com `holmes.py leitura`.")


def vivo(pid):
    return bool(pid) and Path(f"/proc/{pid}").exists()


def abre_execucao(db, t, pid=None, log=None, host=None):
    tt = um(db, "SELECT * FROM teste WHERE no=?", t["id"])
    v = versao_atual(db, tt["instrumento"]) if tt["instrumento"] else None
    if tt["instrumento"] and v:
        inst = um(db, "SELECT * FROM instrumento WHERE no=?", tt["instrumento"])
        s = sha_arquivo(inst["caminho"])
        if s and s != v["sha"]:  # instrumento mudou no disco sem registrar: registra antes de rodar
            vid = db.execute("INSERT INTO versao(instrumento, sha, quando, nota) VALUES (?,?,?,?)",
                             (tt["instrumento"], s, agora(), "detectada ao rodar")).lastrowid
            evento(db, tt["instrumento"], "nova versão", f"{v['sha'][:12]} → {s[:12]} (detectada ao rodar)")
            v = um(db, "SELECT * FROM versao WHERE id=?", vid)
    sha_s = sha_arquivo(tt["script"]) if tt["script"] else None
    if tt["script"] and not sha_s:
        print(f"aviso: script {tt['script']} não encontrado daqui: execução sem versão do script (passe o caminho "
              "absoluto em --script); o resultado aparece 'script não versionado'")
    xid = db.execute("INSERT INTO execucao(teste, versao, script_sha, host, pid, log, inicio) VALUES (?,?,?,?,?,?,?)",
                     (t["id"], v["id"] if v else None, sha_s, host or socket.gethostname(), pid, log, agora())).lastrowid
    db.execute("UPDATE no SET estado='rodando', atualizado=? WHERE id=?", (agora(), t["id"]))
    evento(db, t["id"], "rodando", f"X{xid}" + (f" pid {pid}" if pid else "") + (f" log {log}" if log else ""))
    return xid


# ---------- consultas ----------

def selo(db, r):
    if r["tipo"] == "teste":
        res = resultado_de(db, r["id"])
        v = validade(db, r["id"])
        return (f"→{res}" if res else "") + (f" ⚠ {v}" if v else "")
    if r["tipo"] == "pista":
        f = um(db, "SELECT * FROM fato WHERE no=?", r["id"])
        return f" {f['natureza']}/{r['origem']}/{r['grau'] or '-'}" if f else ""
    if r["tipo"] == "fato":
        f = um(db, "SELECT * FROM fato WHERE no=?", r["id"])
        return f" {f['natureza']}/{r['origem']}/{r['grau'] or '-'}" + (f" provado:{f['conferido_por']}" if f["conferido"] and f["conferido_por"]
                                                                            else "" if f["conferido"] else " não-provado")
    if r["tipo"] == "hipotese":
        h = um(db, "SELECT prob FROM hipotese WHERE no=?", r["id"])
        return f" p={h['prob']:.2f}" if h and h["prob"] is not None else ""
    return ""


def linha(db, r):
    marca = "✗ " if r["estado"] in CAIDOS else ""
    return f"{marca}{rot(r)} [{r['tipo']}:{r['estado']}{selo(db, r)}] {r['titulo']}"


def expande(db, texto):
    """Acrescenta à consulta os aliases das entidades cujo nome ou alias aparece no texto."""
    ws = set(C.termos(texto))
    extra = []
    for e in q(db, "SELECT n.titulo, e.aliases FROM entidade e JOIN no n ON n.id=e.no"):
        nomes = [e["titulo"]] + [a.strip() for a in (e["aliases"] or "").split(",") if a.strip()]
        if any(set(C.termos(nm)) & ws for nm in nomes):
            extra += nomes
    return texto + " " + " ".join(extra)


def busca(db, texto, n=8, so_testes=False, com_corpus=True):
    ws = C.termos(expande(db, texto))
    saida = []
    if ws:
        for h in q(db, "SELECT ref FROM idx WHERE idx MATCH ? ORDER BY bm25(idx) LIMIT ?",
                   " OR ".join(f'"{w}"' for w in ws), n * 4):
            r = um(db, "SELECT * FROM no WHERE id=?", int(h["ref"]))
            if not r or (so_testes and r["tipo"] != "teste"):
                continue
            s = linha(db, r)
            if so_testes:
                t = um(db, "SELECT * FROM teste WHERE no=?", r["id"])
                x = ultima(db, r["id"])
                s += f"\n    alcance: {t['alcance']}" + (f"\n    fora: {t['fora']}" if t["fora"] else "")
                if x and x["nota"]:
                    s += f"\n    resultado: {x['nota'][:200]}"
            saida.append(s)
            if len(saida) >= n:
                break
    if com_corpus and not so_testes and C.existe():
        try:
            with C.conecta() as cdb:
                saida += [f"corpus {C.linha(C.pedaco(cdb, i), texto)}" for i in C.bm25(cdb, texto, n=3)]
        except Exception as e:  # corpus é auxiliar; a busca no caso não depende dele
            saida.append(f"(corpus indisponível: {e})")
    return saida


def dependencias_quebradas(db):
    return q(db, "SELECT a.de, a.para, a.tipo FROM aresta a JOIN no d ON d.id=a.de JOIN no p ON p.id=a.para "
                 f"WHERE a.tipo IN ('depende','deriva') AND p.estado IN ({','.join('?' * len(CAIDOS))}) "
                 f"AND d.estado NOT IN ({','.join('?' * len(CAIDOS))}) AND d.estado != 'substituida'", *CAIDOS, *CAIDOS)


def contradicoes(db):
    return q(db, "SELECT a.de, a.para FROM aresta a JOIN no d ON d.id=a.de JOIN no p ON p.id=a.para "
                 f"WHERE a.tipo='contradiz' AND p.estado NOT IN ({','.join('?' * len(CAIDOS))}) "
                 f"AND d.estado NOT IN ({','.join('?' * len(CAIDOS))})", *CAIDOS, *CAIDOS)


def alvo_livre(db, a):
    deps = q(db, "SELECT n.estado FROM aresta x JOIN no n ON n.id=x.para WHERE x.de=? AND x.tipo='depende' "
                 "AND n.tipo='alvo'", a)
    return all(d["estado"] == "resolvido" for d in deps)


def mapa(db, caso, tudo=False):
    """Plano geral em seções com orçamento fixo, na ordem do que mais importa: nada de uma seção grande
    empurrar alertas, decisões e fios para fora (o defeito do painel do v1)."""
    L = [f"# MAPA — {caso}  ({agora()[:16]} UTC)"]
    rid = lambda i: rot(um(db, "SELECT * FROM no WHERE id=?", i))
    lim = (lambda n: 10 ** 6) if tudo else (lambda n: n)
    mais = lambda rs, n, dica: [f"    … +{len(rs) - n} ({dica})"] if len(rs) > n and not tudo else []
    for o in q(db, "SELECT * FROM no WHERE tipo='objetivo'"):
        L.append(f"OBJETIVO {rot(o)} [{o['estado']}]: {o['titulo']}" + (f"\n  {o['resumo'][:300]}" if o["resumo"] else ""))
    lt = leitura_atual(db)
    if lt:
        L.append(f"\nLEITURA ATUAL {rot(lt)} ({lt['criado'][:10]}; {resultados_sem_leitura(db)} resultados desde então):\n  "
                 + " ".join((lt["resumo"] or lt["titulo"]).split())[:lim(400)] + ("…" if len(lt["resumo"] or "") > 400 and not tudo else ""))
        base = base_leitura(db, lt)
        L.append("  " + (base or "sem base ligada: `leitura ... --sustenta E..` liga a teoria às evidências"))
    else:
        L.append("\nLEITURA ATUAL: nenhuma. Escreva o que o caso parece contar e onde estamos nessa história: "
                 "`holmes.py leitura \"...\"`.")
    ra = ramo_ativo(db, caso)
    nr = {e: c for e, c in q(db, "SELECT estado, count(*) FROM no WHERE tipo='ramo' GROUP BY estado")}
    if ra:
        ps = passos_de(db, ra["id"])
        L.append(f"\nRAMO ATIVO {rot(ra)}: {ra['titulo'][:110]}  ({nr.get('ativo', 0)} ativos, {nr.get('pausado', 0)} "
                 "pausados; `ficha`, `trilha`, `arvore`)")
        L += [f"  {j}. {p['tipo']}: {p['texto'][:110]}" for j, p in list(enumerate(ps, 1))[-2:]]
    elif nr:
        L.append(f"\nRAMO ATIVO: nenhum ({sum(nr.values())} ramos; `arvore` mostra, `ramo usa B..` escolhe)")
    px = proximo(db)
    L.append("PRÓXIMO (`proximo`): " + " | ".join(f"{a} — {p[:90]}" for a, p in px[:lim(2)]))
    alvos = q(db, "SELECT * FROM no WHERE tipo='alvo' ORDER BY id")
    abertos = [a for a in alvos if a["estado"] != "resolvido"]
    if alvos:
        L.append(f"\nALVOS ({len(abertos)} abertos de {len(alvos)}):")
        for a in abertos[:lim(8)]:
            deps = q(db, "SELECT para FROM aresta WHERE de=? AND tipo='depende'", a["id"])
            livre = a["estado"] == "aberto" and deps and alvo_livre(db, a["id"])
            L.append(f"  {rot(a)} [{a['estado']}{' · DESBLOQUEADO' if livre else ''}] {a['titulo'][:90]}"
                     + (f" (depende de {', '.join(rid(d['para']) for d in deps)})" if deps else ""))
        L += mais(abertos, 8, "`mapa --tudo`")
        feitos = [a for a in alvos if a["estado"] == "resolvido"]
        if feitos:
            L.append(f"  resolvidos ({len(feitos)}): " + ", ".join(rot(a) for a in feitos) + "  (`ver <id>` dá solução e prova)")
    frentes = q(db, "SELECT * FROM no WHERE tipo='frente' AND estado='ativa' ORDER BY id")
    L.append(f"\nFRENTES ATIVAS ({len(frentes)}/{MAX_FRENTES}):")
    alertas = []
    for f in frentes:
        L.append(f"  {rot(f)} {f['titulo'][:90]}" + (f" — {f['resumo'][:100]}" if f["resumo"] else ""))
        hs = q(db, "SELECT n.*, h.prob FROM no n JOIN hipotese h ON h.no=n.id WHERE n.pai=? AND n.estado IN "
                   "('viva','apoiada') ORDER BY h.prob DESC, n.id", f["id"])
        for h in hs[:lim(2)]:
            ts = q(db, "SELECT id FROM no WHERE pai=? AND tipo='teste'", h["id"])
            neg = sum(1 for t in ts if resultado_de(db, t["id"]) == "negativo")
            p = f" p={h['prob']:.2f}" if h["prob"] is not None else ""
            L.append(f"    {rot(h)} [{h['estado']}{p}] {h['titulo'][:80]}" + (f"  (formas testadas {len(ts)}, neg {neg})" if ts else ""))
        L += mais(hs, 2, f"`ver {rot(f)}`")
        prem = q(db, "SELECT * FROM no WHERE pai=? AND tipo='premissa' AND estado='assumida'", f["id"])
        if prem:
            L.append(f"    premissas não verificadas: " + ", ".join(rot(r) for r in prem[:lim(6)]))
        n, v = tunel(db, f["id"])
        if n >= TUNEL:
            alertas.append(("túnel", f"TÚNEL em {rot(f)}: {aviso_tunel(n, v)}. Pare de testar: LEITURA, releia premissas "
                           "e fonte primária, procure leituras alternativas, leve ao usuário."))
    prem_obj = q(db, "SELECT id FROM no WHERE tipo='premissa' AND estado='assumida' AND pai IN "
                     "(SELECT id FROM no WHERE tipo IN ('objetivo','alvo'))")
    if prem_obj:
        L.append(f"  premissas gerais não verificadas ({len(prem_obj)}): " + ", ".join(f"R{r['id']}" for r in prem_obj[:lim(8)]))
    qs = q(db, "SELECT * FROM no WHERE tipo='questao' AND estado='aberta' AND legado=0 ORDER BY id DESC")
    if qs:
        L.append(f"\nQUESTÕES ABERTAS ({len(qs)}; `questoes`):")
        for x in qs[:lim(3)]:
            sem = not um(db, "SELECT 1 FROM aresta WHERE para=? AND tipo='responde'", x["id"])
            L.append(f"  {rot(x)} {x['titulo'][:90]}" + (" [lacuna: sem hipótese]" if sem else ""))
    nc = um(db, "SELECT count(*) FROM no WHERE tipo='conexao' AND estado='sugerida'")[0]
    if nc:
        L.append(f"  conexões candidatas por avaliar: {nc} (`conexoes` lista; confirmar ou rejeitar com `estado C..`)")
    abertos_t = q(db, "SELECT * FROM no WHERE tipo='teste' AND estado IN ('planejado','rodando') ORDER BY id")
    for t in abertos_t:
        x = um(db, "SELECT * FROM execucao WHERE teste=? AND resultado IS NULL ORDER BY id DESC", t["id"])
        if x and x["pid"] and not vivo(x["pid"]):
            alertas.append(("pid", f"{rot(t)} 'rodando' com PID morto: leia o log e registre o resultado."))
    lida = pede_leitura(db)
    if lida:
        alertas.insert(0, ("leitura", lida))
    # Itens herdados de outro sistema (legado=1) não entram nos alertas até alguém mexer neles: senão a dívida
    # antiga afoga o sinal novo. Ficam numa linha de contagem, e inteiros em `saude`.
    leg = lambda i: um(db, "SELECT legado FROM no WHERE id=?", i)[0]
    herdado = {}
    for d in dependencias_quebradas(db):
        if leg(d["de"]) and leg(d["para"]):
            herdado["dependências quebradas"] = herdado.get("dependências quebradas", 0) + 1
        else:
            alertas.append(("dep", f"{rid(d['de'])} {d['tipo']} de {rid(d['para'])}, que caiu: reavalie {rid(d['de'])}."))
    for c in contradicoes(db):
        if leg(c["de"]) and leg(c["para"]):
            herdado["contradições"] = herdado.get("contradições", 0) + 1
        else:
            alertas.append(("contra", f"contradição aberta: {rid(c['de'])} × {rid(c['para'])} (retrate um ou resolva)."))
    sel = [(validade(db, t["no"]), t["legado"]) for t in q(db, "SELECT t.no, n.legado FROM teste t JOIN no n ON n.id=t.no")]
    for chave, txt in (("INDETERMINADO", "negativo(s) sem instrumento: INDETERMINADOS, não fecham nada"),
                       ("A REVALIDAR", "negativo(s) julgados por versão antiga do instrumento: A REVALIDAR"),
                       ("INVÁLIDO", "resultado(s) com controle falho: INVÁLIDOS")):
        n = sum(1 for v, lg in sel if v.startswith(chave) and not lg)
        if n:
            alertas.append((chave, f"{n} {txt}."))
        nl = sum(1 for v, lg in sel if v.startswith(chave) and lg)
        if nl:
            herdado[{"INDETERMINADO": "negativos indeterminados", "A REVALIDAR": "negativos a revalidar",
                     "INVÁLIDO": "resultados inválidos"}[chave]] = nl
    rasc = um(db, "SELECT count(*) FROM no WHERE tipo='pista' AND estado='aberta' AND legado=0")[0]
    if rasc:
        alertas.append(("rasc", f"{rasc} pista(s) aberta(s): provar (`confere K.. --por ..`, vira fato) ou descartar "
                                "(`estado K.. descartada`)."))
    if herdado:
        alertas.append(("legado", "herdado, fora dos alertas: " + ", ".join(f"{v} {k}" for k, v in herdado.items())
                        + ". Trie um alvo por vez (`saude`); mexer num item o traz de volta."))
    if alertas:
        # agrupa os do mesmo tipo para que um tipo repetido não esconda os outros
        grupos = {}
        for k, a in alertas:
            grupos.setdefault(k, []).append(a)
        vis = [g[0] + (f"  (+{len(g) - 1} do mesmo tipo: `saude`)" if len(g) > 1 else "")
               for g in grupos.values()] if not tudo else [a for _, a in alertas]
        L.append(f"\nALERTAS ({len(alertas)}):")
        L += [f"  ⚠ {a}" for a in vis[:lim(7)]]
    front = q(db, "SELECT h.* FROM no h JOIN no f ON f.id=h.pai WHERE h.tipo='hipotese' AND h.estado='viva' "
                  "AND f.estado='ativa' AND NOT EXISTS (SELECT 1 FROM no t WHERE t.pai=h.id AND t.tipo='teste' "
                  "AND t.estado IN ('planejado','rodando')) ORDER BY h.id")
    if front:
        L.append(f"\nFRONTEIRA ({len(front)} hipóteses vivas sem teste aberto): " + ", ".join(rot(h) for h in front[:lim(12)])
                 + (" …" if len(front) > 12 and not tudo else ""))
    if abertos_t:
        L.append("\nTESTES ABERTOS:")
        for t in abertos_t[:lim(5)]:
            x = um(db, "SELECT * FROM execucao WHERE teste=? AND resultado IS NULL ORDER BY id DESC", t["id"])
            pid = f" X{x['id']} pid {x['pid']} {'vivo' if vivo(x['pid']) else 'MORTO'}" if x and x["pid"] else ""
            L.append(f"  {rot(t)} [{t['estado']}{pid}] {t['titulo'][:90]}" + (f" log {x['log']}" if x and x["log"] else ""))
        L += mais(abertos_t, 5, "`jobs`")
    for titulo, sql, n in (("DECISÕES DO USUÁRIO (valem sobre qualquer regra)",
                            "SELECT * FROM no WHERE tipo='decisao' AND estado='vigente' AND origem='usuario' ORDER BY id DESC", 3),
                           ("FIOS ABERTOS", "SELECT * FROM no WHERE tipo='fio' AND estado='aberto' ORDER BY id DESC", 5)):
        rs = q(db, sql)
        if rs:
            L.append(f"\n{titulo} ({len(rs)}):")
            for r in rs[:lim(n)]:
                d = um(db, "SELECT * FROM decisao WHERE no=?", r["id"])
                L.append(f"  {rot(r)} {r['titulo'][:100]}" + (f" | proíbe: {d['proibe'][:60]}" if d and d["proibe"] else "")
                         + (f" | permite: {d['permite'][:60]}" if d and d["permite"] else ""))
            L += mais(rs, n, "`mapa --tudo`")
    outras = um(db, "SELECT count(*) FROM no WHERE tipo='decisao' AND estado='vigente' AND origem!='usuario'")[0]
    if outras:
        L.append(f"  (+{outras} decisões de método do agente: consulte com `busca`)")
    ev = q(db, "SELECT e.*, n.tipo, n.id nid FROM evento e LEFT JOIN no n ON n.id=e.no ORDER BY e.id DESC LIMIT ?",
           20 if tudo else 3)
    if ev:
        L.append("\nÚLTIMOS EVENTOS:")
        L += [f"  {e['quando'][:16]} {PREFIXO.get(e['tipo'], '')}{e['nid'] or ''} {e['acao']}: {' '.join((e['texto'] or '').split())[:90]}"
              for e in ev]
    L.append("\nDetalhe sob demanda: `ver <id>`, `busca`, `ja`, `saude`. "
             "Não leia documentos inteiros para se orientar.")
    txt = "\n".join(L)
    if not tudo and len(txt) > MAX_MAPA and "\n\nÚLTIMOS EVENTOS:" in txt:  # eventos são o que menos orienta
        ini = txt.index("\n\nÚLTIMOS EVENTOS:")
        txt = txt[:ini] + txt[txt.index("\n\nDetalhe sob demanda", ini):]
    if not tudo and len(txt) > MAX_MAPA:
        txt = txt[:MAX_MAPA - 110] + "\n… [mapa cortado para caber na abertura; inteiro: `holmes.py mapa --tudo`]"
    return txt


def ver(db, r):
    L = [linha(db, r), f"  origem {r['origem']} · criado {r['criado'][:16]} · atualizado {r['atualizado'][:16]}"]
    if r["resumo"]:
        L.append(f"  {r['resumo']}")
    p, cadeia = r, []
    while p["pai"]:
        p = um(db, "SELECT * FROM no WHERE id=?", p["pai"])
        cadeia.append(f"{rot(p)} {p['titulo'][:50]}")
    if cadeia:
        L.append("  sob: " + " ← ".join(cadeia))
    if r["ramo"] if "ramo" in r.keys() else None:
        rm = um(db, "SELECT * FROM no WHERE id=?", r["ramo"])
        L.append(f"  no ramo: {rot(rm)} [{rm['estado']}] {rm['titulo'][:80]}")
    for tab in ("teste", "fato", "hipotese", "alvo", "decisao", "entidade", "fonte", "instrumento", "conexao"):
        x = um(db, f"SELECT * FROM {tab} WHERE no=?", r["id"]) if tab == r["tipo"] or (tab, r["tipo"]) == ("fato", "pista") else None
        if x:
            L += [f"  {k}: {x[k]}" for k in x.keys() if k != "no" and x[k] not in (None, "")]
    if r["tipo"] == "teste":
        t = um(db, "SELECT * FROM teste WHERE no=?", r["id"])
        for x in q(db, "SELECT x.*, v.sha FROM execucao x LEFT JOIN versao v ON v.id=x.versao WHERE x.teste=? "
                       "ORDER BY x.id", r["id"]):
            antes = ("previsão ANTES" if t["previsao_em"] and t["previsao_em"] <= (x["inicio"] or "")
                     else "previsão depois ou ausente")
            L.append(f"  X{x['id']} {x['inicio'][:16]}→{(x['fim'] or '…')[:16]} {x['resultado'] or 'rodando'} "
                     f"instr {(x['sha'] or 'nenhum')[:12]} controle_ok={x['controle_ok']} n={x['n']} {antes} "
                     f"{x['host']} pid {x['pid']} log {x['log']}" + (f"\n     {x['nota']}" if x["nota"] else "")
                     + (f"\n     sentido: {x['sentido']}" if x["sentido"] else ""))
        v = validade(db, r["id"])
        if v:
            L.append(f"  ⚠ {v}")
    if r["tipo"] == "instrumento":
        L += [f"  versão {v['id']} {v['sha'][:12]} {v['quando'][:16]} verificado={v['verificado']} {v['nota'] or ''}"
              for v in q(db, "SELECT * FROM versao WHERE instrumento=? ORDER BY id", r["id"])]
    if r["tipo"] == "entidade":
        L += [f"  · {a['chave']} = {a['valor']}" + (f" (E{a['fato']})" if a["fato"] else "")
              for a in q(db, "SELECT * FROM atributo WHERE entidade=? ORDER BY chave", r["id"])]
    if r["tipo"] == "hipotese":
        for a in q(db, "SELECT a.valor, n.* FROM ach a JOIN no n ON n.id=a.fato WHERE a.hipotese=?", r["id"]):
            L.append(f"  ACH {a['valor']:>2} {rot(a)} {a['titulo'][:70]}")
    if r["tipo"] == "conexao":
        c = um(db, "SELECT * FROM conexao WHERE no=?", r["id"])
        for k in ("de", "para"):
            L.append(f"  {k}: {linha(db, um(db, 'SELECT * FROM no WHERE id=?', c[k]))[:140]}")
    if r["tipo"] == "leitura":
        L.append("  " + (base_leitura(db, r) or "sem base ligada"))
    for c in q(db, "SELECT c.*, n.estado, n.titulo FROM conexao c JOIN no n ON n.id=c.no WHERE c.de=? OR c.para=?",
               r["id"], r["id"]):
        L.append(f"  ~ conexão candidata C{c['no']} [{c['estado']}] {c['titulo'][:90]}")
    fs = q(db, "SELECT * FROM no WHERE pai=? ORDER BY id", r["id"])
    if fs:
        L.append("  filhos:")
        L += [f"    {linha(db, f)}" for f in fs[:30]]
    for seta, sql in (("→", "SELECT a.tipo t, a.nota, n.* FROM aresta a JOIN no n ON n.id=a.para WHERE a.de=?"),
                      ("←", "SELECT a.tipo t, a.nota, n.* FROM aresta a JOIN no n ON n.id=a.de WHERE a.para=?")):
        for x in q(db, sql, r["id"]):
            caiu = " (CAIU)" if x["estado"] in CAIDOS else ""
            L.append(f"  {seta} {x['t']} {rot(x)} {x['titulo'][:70]}{caiu}" + (f" — {x['nota']}" if x["nota"] else ""))
    L += [f"  · {e['quando'][:16]} {e['acao']}: {e['texto']}"
          for e in q(db, "SELECT * FROM evento WHERE no=? ORDER BY id DESC LIMIT 8", r["id"])]
    return "\n".join(L)


def matriz_ach(db, f):
    hs = q(db, "SELECT * FROM no WHERE pai=? AND tipo='hipotese' AND estado IN ('viva','apoiada') ORDER BY id", f["id"])
    if not hs:
        return f"{rot(f)} sem hipóteses vivas"
    vals = q(db, f"SELECT * FROM ach WHERE hipotese IN ({','.join('?' * len(hs))})", *[h["id"] for h in hs])
    fatos = sorted({v["fato"] for v in vals})
    cel = {(v["fato"], v["hipotese"]): v["valor"] for v in vals}
    L = ["fato    " + " ".join(f"{rot(h):>6}" for h in hs) + "  diagnóstico?"]
    for e in fatos:
        linha_v = [cel.get((e, h["id"]), "·") for h in hs]
        diag = "sim" if len({x for x in linha_v if x != "·"}) > 1 else "não (igual para todas)"
        L.append(f"E{e:<6} " + " ".join(f"{x:>6}" for x in linha_v) + f"  {diag}")
    inc = [sum(-ACH[cel[(e, h['id'])]] for e in fatos if (e, h["id"]) in cel and ACH[cel[(e, h['id'])]] < 0) for h in hs]
    L.append("inconsist " + " ".join(f"{x:>6}" for x in inc) + "  (menor = menos refutada; conta só I/II)")
    return "\n".join(L)


def saude(db):
    L = []
    orf = q(db, "SELECT * FROM no WHERE tipo='fato' AND id NOT IN (SELECT de FROM aresta UNION SELECT para FROM aresta "
                "UNION SELECT fato FROM ach)")
    if orf:
        L.append(f"{len(orf)} fato(s) soltos, sem ligação a hipótese/entidade: " + ", ".join(rot(r) for r in orf[:15]))
    sem_fonte = q(db, "SELECT n.* FROM no n JOIN fato f ON f.no=n.id WHERE n.origem IN ('autor','fonte') "
                      "AND f.fonte IS NULL AND n.estado != 'retratado'")
    if sem_fonte:
        L.append(f"{len(sem_fonte)} fato(s) de origem autor/fonte sem --fonte: " + ", ".join(rot(r) for r in sem_fonte[:15]))
    velhos = q(db, "SELECT * FROM no WHERE tipo='teste' AND estado='planejado' AND criado < datetime('now','-3 day')")
    if velhos:
        L.append(f"{len(velhos)} teste(s) planejados há mais de 3 dias: " + ", ".join(rot(r) for r in velhos[:15]))
    deps = dependencias_quebradas(db)
    if deps:
        L.append(f"{len(deps)} item(ns) dependem de algo que caiu (refutado/retratado): "
                 + ", ".join(f"{d['de']}→{d['para']}" for d in deps[:40]) + (" …" if len(deps) > 40 else ""))
    cs = contradicoes(db)
    if cs:
        L.append(f"{len(cs)} contradição(ões) abertas: " + ", ".join(f"{c['de']}×{c['para']}" for c in cs[:40]))
    hs = q(db, "SELECT n.* FROM no n JOIN hipotese h ON h.no=n.id WHERE n.estado='viva' AND h.refuta_se IS NULL")
    if hs:
        L.append(f"{len(hs)} hipótese(s) viva(s) sem critério de refutação (--refuta-se): " + ", ".join(rot(r) for r in hs[:15]))
    hk = RAIZ / ".holmes" / "hooks.json"  # gravado pelos próprios hooks ao rodar: execução vista, não configuração
    try:
        import json
        vistos = json.loads(hk.read_text()) if hk.exists() else {}
    except (OSError, ValueError):
        vistos = {}
    if not isinstance(vistos, dict):
        vistos = {}
    falta = [h for h in ("abertura", "pistas", "guarda", "fim") if h not in vistos]
    L.append("hooks vistos rodando: " + (", ".join(f"{k} {v}" for k, v in sorted(vistos.items())) or "nenhum")
             + (f" · nunca vistos: {', '.join(falta)} (confira .claude/settings.json e a confiança na pasta)" if falta else ""))
    return "\n".join(L)


# ---------- relações: descoberta (consulta) e conexões candidatas (registro) ----------

VAZIAS = set("para com que uma por como mais mas não nao das dos nas nos pelo pela este esta isso isto "
             "ser são foi tem the and that this with from have for are was were which".split())
NUM = re.compile(r"\b(?:\d{2,}|[0-9a-f]{6,})\b", re.I)
SALIENTES = ("fato", "pista", "hipotese", "questao", "entidade", "premissa", "fio", "leitura")


def texto_de(db, r):
    f = um(db, "SELECT citacao FROM fato WHERE no=?", r["id"])
    return " ".join([r["titulo"], r["resumo"] or "", (f["citacao"] or "") if f else ""])


def todos(texto):  # C.termos corta em 24 termos (bom para consulta, ruim para comparar textos longos)
    return set(re.findall(r"\w{3,}", texto.lower()))


def palavras(texto):
    return {w for w in todos(texto) if len(w) >= 4 and w not in VAZIAS and not w.isdigit()}


def vizinhos(db, no):
    return {x[0] for x in q(db, "SELECT para FROM aresta WHERE de=? UNION SELECT de FROM aresta WHERE para=?", no, no)}


def fts(db, termos, junta="OR", n=30):
    if not termos:
        return []
    return [int(h["ref"]) for h in q(db, "SELECT ref FROM idx WHERE idx MATCH ? ORDER BY bm25(idx) LIMIT ?",
                                     f" {junta} ".join(f'"{w}"' for w in termos), n)]


def candidatas(db, texto, no=None, n=8):
    """Relações possíveis para um item (ou um texto), por cinco canais baratos. Nada é gravado: é consulta.
    O julgamento de que a relação existe é do agente, e a confirmação, de uma evidência (`conexao`/`estado`).
    Canais: termos em comum; ponte por entidade (nome ↔ alias da mesma entidade, a via para o que não
    compartilha palavra); vizinho comum no grafo; mesmo número ou sequência; material do corpus."""
    ws, nums = palavras(texto), {m.lower() for m in NUM.findall(texto)}
    motivos = {}

    def add(i, canal, txt):
        if i != no:
            motivos.setdefault(i, {}).setdefault(canal, txt)

    for i in fts(db, sorted(ws)[:60]):
        comuns = ws & palavras(texto_de(db, um(db, "SELECT * FROM no WHERE id=?", i)))
        if len(comuns) >= (2 if len(ws) > 6 else 1):
            add(i, "termos", "termos em comum: " + ", ".join(sorted(comuns)[:4]))
    for e in q(db, "SELECT n.id, n.titulo, e.aliases FROM entidade e JOIN no n ON n.id=e.no WHERE n.estado='ativa'"):
        nomes = [e["titulo"]] + [a.strip() for a in (e["aliases"] or "").split(",") if a.strip()]
        bate = [nm for nm in nomes if todos(nm) and todos(nm) <= todos(texto)]
        if not bate or e["id"] == no:
            continue
        add(e["id"], "ponte", f"entidade de que o texto fala ('{bate[0]}')")
        for nm in nomes:
            if nm in bate:
                continue
            for i in fts(db, C.termos(nm), "AND", 15):
                outro = um(db, "SELECT * FROM no WHERE id=?", i)
                if not todos(nm) <= todos(texto_de(db, outro)):
                    continue
                add(i, "ponte", f"ponte N{e['id']} {e['titulo']}: '{bate[0]}' ↔ '{nm}'")
        for i in vizinhos(db, e["id"]):
            add(i, "ponte", f"ligado à entidade N{e['id']} {e['titulo']} ('{bate[0]}')")
    if no:
        for v in vizinhos(db, no):
            for i in vizinhos(db, v) - {no}:
                add(i, "grafo", f"vizinho comum {rot(um(db, 'SELECT * FROM no WHERE id=?', v))}")
    for m in nums:
        for i in fts(db, [m], n=15):
            add(i, "numero", f"mesmo número/sequência {m}")
    ja = vizinhos(db, no) if no else set()
    reg = {}
    if no:
        for c in q(db, "SELECT c.*, n.estado FROM conexao c JOIN no n ON n.id=c.no WHERE c.de=? OR c.para=?", no, no):
            reg[c["para"] if c["de"] == no else c["de"]] = (c["no"], c["estado"])
    linhas, cont = [], {"ligados": 0, "rejeitadas": 0}
    peso = {"ponte": 3, "numero": 2, "grafo": 2, "termos": 1}
    ordem = sorted(motivos.items(), key=lambda kv: (-sum(peso[c] for c in kv[1]), -kv[0]))
    for i, ms in ordem:
        r = um(db, "SELECT * FROM no WHERE id=?", i)
        if not r or r["tipo"] not in SALIENTES or r["estado"] in CAIDOS:
            continue
        if i in ja:
            cont["ligados"] += 1
            continue
        nota = ""
        if i in reg:
            if reg[i][1] == "rejeitada":
                cont["rejeitadas"] += 1
                continue
            nota = f"  (já registrada: C{reg[i][0]} {reg[i][1]})"
        linhas.append(f"  {linha(db, r)[:150]}{' (v1)' if r['legado'] else ''}{nota}\n      ← " + "; ".join(ms.values()))
    saida = linhas[:n]
    rodape = [f"(+{len(linhas) - n} candidatas)"] if len(linhas) > n else []
    rodape += [f"({cont['ligados']} já ligados no grafo, {cont['rejeitadas']} já rejeitadas: fora da lista)"] if any(cont.values()) else []
    if C.existe():
        try:
            with C.conecta() as cdb:
                try:
                    ids = C.busca(cdb, texto, n=3, modo="hibrido")
                except Exception:  # sem vetores: só palavra
                    ids = C.bm25(cdb, texto, n=3)
                saida += [f"  material {C.linha(C.pedaco(cdb, i), texto)[:150]}  (corpus, não registrado: `cita` se importar)"
                          for i in ids]
        except Exception as e:
            rodape.append(f"(corpus indisponível: {e})")
    return saida, rodape


def dependentes(db, no):
    """Tudo que se apoia em `no`, transitivamente: X depende/deriva de no, ou no sustenta X."""
    vistos, fila = [], [no]
    while fila:
        a = fila.pop()
        for x in q(db, "SELECT de i FROM aresta WHERE para=? AND tipo IN ('depende','deriva') "
                       "UNION SELECT para FROM aresta WHERE de=? AND tipo='sustenta'", a, a):
            if x["i"] not in vistos and x["i"] != no:
                vistos.append(x["i"])
                fila.append(x["i"])
    return vistos


def cadeia(db, r, prof=0, visto=None, rotulo=""):
    """A fundamentação de um item, descendo: de que depende, o que o sustenta ou enfraquece, até a fonte."""
    visto = visto if visto is not None else set()
    visto.add(r["id"])
    caiu = "  ⚠ CAIU" if r["estado"] in CAIDOS else ""
    L = [("    " * prof) + (f"{rotulo} " if rotulo else "") + linha(db, r)[:140] + caiu]
    if prof >= 4:
        return L
    filhos = [(x["tipo"], x["id"]) for x in q(db, "SELECT a.tipo, n.id FROM aresta a JOIN no n ON n.id=a.para WHERE a.de=? "
                                                  "AND a.tipo IN ('depende','deriva','responde')", r["id"])]
    filhos += [(f"←{x['tipo']}", x["id"]) for x in q(db, "SELECT a.tipo, n.id FROM aresta a JOIN no n ON n.id=a.de "
                                                         "WHERE a.para=? AND a.tipo IN ('sustenta','enfraquece','refuta',"
                                                         "'contradiz','rival')", r["id"])]
    filhos += [(f"ACH {x['valor']}", x["fato"]) for x in q(db, "SELECT * FROM ach WHERE hipotese=?", r["id"])]
    for rotulo_f, i in filhos:
        if i not in visto:
            L += cadeia(db, um(db, "SELECT * FROM no WHERE id=?", i), prof + 1, visto, rotulo_f)
    return L


def questoes(db):
    L = []
    for x in q(db, "SELECT * FROM no WHERE tipo='questao' AND estado='aberta' ORDER BY legado, id"):
        hs = q(db, "SELECT n.*, h.prob FROM aresta a JOIN no n ON n.id=a.de JOIN hipotese h ON h.no=n.id "
                   "WHERE a.para=? AND a.tipo='responde' AND n.estado IN ('viva','apoiada')", x["id"])
        pistas = um(db, "SELECT count(*) FROM aresta WHERE para=? AND tipo='sobre'", x["id"])[0]
        L.append(f"{rot(x)} {x['titulo'][:100]}" + (" (v1)" if x["legado"] else "") + "\n    "
                 + (f"{len(hs)} hipótese(s): " + ", ".join(rot(h) + (f" p={h['prob']:.2f}" if h["prob"] is not None else "")
                                                         for h in hs) if hs else "LACUNA: nenhuma hipótese ainda")
                 + f" · {pistas} pista(s) ligada(s)")
    feitas = um(db, "SELECT count(*) FROM no WHERE tipo='questao' AND estado!='aberta'")[0]
    return "\n".join(L or ["nenhuma questão aberta: `novo questao \"<pergunta>\" --pai <frente|alvo|O>`"]) + \
        (f"\n({feitas} respondida(s), reformulada(s) ou estacionada(s): `busca`)" if feitas else "")


def proximo(db):
    """Recomendação explicada do próximo passo, por critérios verificáveis no registro (MODELO.md, 'Próximo
    passo'). Não é ranking numérico: a ordem é a dos critérios, do que mais muda o rumo ao que menos muda."""
    R = []
    for f in q(db, "SELECT * FROM no WHERE tipo='frente' AND estado='ativa' AND legado=0"):
        n, v = tunel(db, f["id"])
        if n >= TUNEL:
            R.append((f"LEITURA da frente {rot(f)}, sem testar", f"túnel: {aviso_tunel(n, v)}"))
    lt = leitura_atual(db)
    if lt:
        caiu = [rot(um(db, "SELECT * FROM no WHERE id=?", d["para"])) for d in dependencias_quebradas(db) if d["de"] == lt["id"]]
        if caiu:
            R.append((f"rever a leitura {rot(lt)}", f"perdeu base: {', '.join(caiu)} caiu"))
    ev = eventos_relevantes(db)
    if ev:
        R.append(("rever a leitura de conjunto", "; ".join(ev)))
    revalidar = [t for t in q(db, "SELECT n.* FROM no n JOIN teste t ON t.no=n.id WHERE n.legado=0")
                 if validade(db, t["id"]).startswith("A REVALIDAR")]
    if revalidar:
        R.append((f"rodar de novo {', '.join(rot(t) for t in revalidar[:3])} com o instrumento atual (`roda`)",
                  f"o instrumento mudou: {len(revalidar)} negativo(s) deixaram de valer e podem estar sustentando decisões"))
    decisiva = um(db, "SELECT n.* FROM aresta a JOIN no n ON n.id=a.para WHERE a.de=? AND a.tipo='sobre' AND "
                      "a.nota='decisiva' AND n.estado='aberta'", lt["id"]) if lt else None
    abertas = ([decisiva] if decisiva else []) + q(db, "SELECT * FROM no WHERE tipo='questao' AND estado='aberta' "
                                                       "AND legado=0 ORDER BY id")
    vistas = set()
    for x in abertas:
        if x["id"] in vistas or len(vistas) >= 2:
            continue
        vistas.add(x["id"])
        tag = "questão decisiva" if decisiva and x["id"] == decisiva["id"] else "questão aberta"
        hs = q(db, "SELECT n.*, h.refuta_se, h.prob FROM aresta a JOIN no n ON n.id=a.de JOIN hipotese h ON h.no=n.id "
                   "WHERE a.para=? AND a.tipo='responde' AND n.estado IN ('viva','apoiada') ORDER BY h.prob DESC", x["id"])
        if not hs:
            R.append((f"formular explicações para {rot(x)}", f"{tag} sem nenhuma hipótese (lacuna): {x['titulo'][:70]}"))
        elif len(hs) == 1:
            R.append((f"gerar ao menos uma rival de {rot(hs[0])} para {rot(x)}", f"{tag} com uma explicação só"))
        else:
            ids = [h["id"] for h in hs]
            cel = q(db, f"SELECT fato, group_concat(DISTINCT valor) v FROM ach WHERE hipotese IN ({','.join('?' * len(ids))}) "
                        "GROUP BY fato", *ids)
            if not any("," in (c["v"] or "") for c in cel):
                R.append((f"achar o discriminador entre {', '.join(rot(h) for h in hs[:3])}",
                          f"{tag}: nenhuma evidência registrada (ACH) pesa diferente entre elas"))
            else:
                h = hs[0]
                R.append((f"teste que separe {rot(h)} das rivais" if h["refuta_se"] else f"dar --refuta-se a {rot(h)}",
                          f"{tag}: há discriminação, a líder p={h['prob']}"))
    cs = q(db, "SELECT c.*, n.id cid FROM conexao c JOIN no n ON n.id=c.no WHERE n.estado='sugerida' ORDER BY n.id")
    if cs:
        cruza = [c for c in cs if raiz_frente(db, c["de"]) != raiz_frente(db, c["para"])]
        c = (cruza or cs)[0]
        R.append((f"avaliar a conexão C{c['cid']} ({len(cs)} sugerida(s))",
                  "liga frentes diferentes" if cruza else "relação candidata parada, nem confirmada nem rejeitada"))
    rasc = q(db, "SELECT DISTINCT n.* FROM no n JOIN aresta a ON a.para=n.id WHERE n.tipo='pista' AND n.estado='aberta' "
                 "AND a.tipo IN ('depende','deriva') AND n.legado=0")
    if rasc:
        R.append((f"provar ou descartar a pista {', '.join(rot(r) for r in rasc[:3])}", "há raciocínio apoiado em pista não provada"))
    if not R:
        h = um(db, "SELECT n.*, h.prob FROM no n JOIN hipotese h ON h.no=n.id JOIN no f ON f.id=n.pai WHERE n.estado='viva' "
                   "AND n.legado=0 AND f.estado='ativa' AND h.refuta_se IS NOT NULL AND NOT EXISTS (SELECT 1 FROM no t "
                   "WHERE t.pai=n.id AND t.tipo='teste') ORDER BY h.prob DESC LIMIT 1")
        if h:
            R.append((f"teste discriminativo para {rot(h)}", "hipótese viva com critério e nenhum teste"))
    return R or [("LEITURA da fonte primária ou do último resultado", "nada no registro pede outra coisa: ler melhor "
                  "costuma render mais que testar mais")]


def raiz_frente(db, i):
    r = um(db, "SELECT * FROM no WHERE id=?", i)
    while r and r["tipo"] != "frente" and r["pai"]:
        r = um(db, "SELECT * FROM no WHERE id=?", r["pai"])
    return r["id"] if r and r["tipo"] == "frente" else None


def cronologia(db):
    """Acontecimentos do mundo investigado (entidade --classe evento com atributo `quando`), não o log do banco."""
    ev = q(db, "SELECT n.*, a.valor quando, a.fato FROM no n JOIN entidade e ON e.no=n.id LEFT JOIN atributo a ON "
               "a.entidade=n.id AND a.chave='quando' WHERE e.classe='evento' AND n.estado != 'fundida' ORDER BY a.valor IS NULL, a.valor, n.id")
    return "\n".join(f"{e['quando'] or '????'}  {rot(e)} {e['titulo'][:110]}" + (f"  (E{e['fato']})" if e["fato"] else "  (data sem fato)")
                     for e in ev) or ("nenhum acontecimento: `novo entidade \"<o que aconteceu>\" --classe evento` e "
                                      "`atributo N.. quando 2019-04-01 --fato E..`")


# ---------- ramos: o percurso do raciocínio ----------

def no_id(db, i):
    return um(db, "SELECT * FROM no WHERE id=?", i)


def passos_de(db, ramo):
    return q(db, "SELECT * FROM passo WHERE ramo=? ORDER BY id", ramo)


def linha_passo(p, j, ind):
    s = f"{ind}{j}. {p['tipo']}: {p['texto']}"
    return s + (f"\n{ind}   porque: {p['porque']}" if p["porque"] else "")


def linha_no(db, n):
    extra = ""
    if n["tipo"] == "alvo" and n["estado"] == "resolvido":
        a = um(db, "SELECT solucao FROM alvo WHERE no=?", n["id"])
        extra = f" ✓ {(a['solucao'] or '')[:80]}" if a else ""
    return f"{rot(n)} [{n['estado']}] {n['titulo'][:100]}{extra}"


def ancestrais(db, r):
    """Do tronco até r, inclusive: um galho nunca aparece sem o caminho que leva a ele."""
    cad, i = [], r["id"]
    while i:
        n = no_id(db, i)
        cad.append(n)
        i = n["pai"]
    return cad[::-1]


def corte_em(db, ramo, filho):
    """Passos de `ramo` que o `filho` herdou: até o passo de onde nasceu, ou até a bifurcação que o criou."""
    ps = passos_de(db, ramo["id"])
    dp = um(db, "SELECT de_passo FROM ramo WHERE no=?", filho["id"])
    lim = dp["de_passo"] if dp and dp["de_passo"] else next(
        (p["id"] for p in ps if p["tipo"] == "bifurcou" and f"B{filho['id']}" in (p["nos"] or "").split(",")), None)
    return [(j, p) for j, p in enumerate(ps, 1) if lim is None or p["id"] <= lim]


def trilha(db, r, curto=False):
    cad, L = ancestrais(db, r), []
    for k, n in enumerate(cad):
        ind = "  " * k
        L.append(ind + linha_no(db, n))
        if n["tipo"] != "ramo":
            continue
        ps = corte_em(db, n, cad[k + 1]) if k + 1 < len(cad) else list(enumerate(passos_de(db, n["id"]), 1))
        if curto and len(ps) > 3:
            L.append(f"{ind}  … {len(ps) - 3} passos antes (`trilha {rot(n)}`)")
            ps = ps[-3:]
        L += [linha_passo(p, j, ind + "  ") for j, p in ps]
    filhos = q(db, "SELECT * FROM no WHERE pai=? AND tipo='ramo' ORDER BY id", r["id"])
    if filhos:
        L.append("  " * len(cad) + "galhos daqui: " + "; ".join(f"{rot(g)} [{g['estado']}] {g['titulo'][:60]}" for g in filhos))
    return "\n".join(L)


def arvore(db, caso, raiz=None):
    ativo = ramo_ativo(db, caso)
    mostrar = {r["id"] for r in q(db, "SELECT id FROM no WHERE tipo IN ('objetivo','alvo')")}
    for r in q(db, "SELECT * FROM no WHERE tipo='ramo'"):
        mostrar |= {n["id"] for n in ancestrais(db, r)}
    nos = {i: no_id(db, i) for i in mostrar}
    filhos = {}
    for n in nos.values():
        filhos.setdefault(n["pai"] if n["pai"] in nos else None, []).append(n)
    L = []

    def desce(n, ind):
        mark = "▶ " if ativo and n["id"] == ativo["id"] else ""
        txt = ind + mark + linha_no(db, n)
        if n["tipo"] == "ramo":
            ps = passos_de(db, n["id"])
            dp = um(db, "SELECT de_passo FROM ramo WHERE no=?", n["id"])["de_passo"]
            if dp:
                pr = um(db, "SELECT ramo FROM passo WHERE id=?", dp)
                j = [p["id"] for p in passos_de(db, pr["ramo"])].index(dp) + 1
                txt += f"  (do passo {j})"
            if ps:
                txt += f"\n{ind}    {len(ps)} passos; último: {ps[-1]['tipo']}: {ps[-1]['texto'][:70]}"
        L.append(txt)
        for c in sorted(filhos.get(n["id"], []), key=lambda x: x["id"]):
            desce(c, ind + "  ")

    raizes = [pega(db, raiz)] if raiz else sorted(filhos.get(None, []), key=lambda x: x["id"])
    for n in raizes:
        desce(n, "")
    return "\n".join(L) or "árvore vazia"


def ficha(db, caso):
    """Uma página: onde estamos, por que, o que está resolvido, o que caiu e qual é a próxima experiência."""
    L = [f"# FICHA — {caso}  ({agora()[:16]} UTC)"]
    for o in q(db, "SELECT * FROM no WHERE tipo='objetivo'"):
        L.append(f"OBJETIVO {rot(o)}: {o['titulo']}")
    r = ramo_ativo(db, caso)
    if r:
        cad = ancestrais(db, r)
        L.append(f"\nIMEDIATO {rot(r)}: {r['titulo']}")
        L.append("  caminho: " + " › ".join(f"{rot(n)} {n['titulo'][:40]}" for n in cad[:-1]))
        ps = passos_de(db, r["id"])
        L.append(f"\nÚLTIMOS PASSOS ({len(ps)} no ramo; `trilha` dá todos):")
        L += [linha_passo(p, j, "  ") for j, p in list(enumerate(ps, 1))[-6:]]
        prox = next((p for p in reversed(ps) if p["tipo"] == "proximo"), None)
        L.append("\nPRÓXIMA EXPERIÊNCIA: " + (f"{prox['texto']}" + (f" — porque {prox['porque']}" if prox["porque"] else "")
                                           if prox else "nenhuma registrada: `passo proximo \"...\" --porque \"...\"`"))
        linhagem = {n["id"] for n in cad}
        irmaos = q(db, "SELECT * FROM no WHERE tipo='ramo' AND estado IN ('morto','fundido','concluido') AND pai IN "
                       f"({','.join('?' * len(linhagem))}) ORDER BY id", *linhagem)
        if irmaos:
            L.append("\nJÁ PERCORRIDO AQUI (não refazer sem motivo novo):")
            for g in irmaos:
                m = um(db, "SELECT porque FROM passo WHERE ramo=? AND tipo='mudou' ORDER BY id DESC", g["id"])
                L.append(f"  {rot(g)} [{g['estado']}] {g['titulo'][:70]}" + (f" — {m['porque'][:100]}" if m and m["porque"] else ""))
    else:
        L.append("\nRAMO ATIVO: nenhum. `arvore` mostra os ramos; `ramo usa B..` ou `ramo novo \"...\" --de <id> --porque \"...\"`")
    feitos = q(db, "SELECT n.*, a.solucao FROM no n JOIN alvo a ON a.no=n.id WHERE n.estado='resolvido' ORDER BY n.id")
    if feitos:
        L.append("\nRESOLVIDO (tronco):")
        L += [f"  {rot(a)} {a['titulo'][:70]} — {(a['solucao'] or '')[:80]}" for a in feitos]
    vivos = q(db, "SELECT * FROM no WHERE tipo='ramo' AND estado IN ('ativo','pausado') ORDER BY id")
    outros = [g for g in vivos if not r or g["id"] != r["id"]]
    if outros:
        L.append(f"\nOUTRAS LINHAS ABERTAS ({len(outros)}):")
        L += [f"  {rot(g)} [{g['estado']}] {g['titulo'][:90]}" for g in outros[:8]]
    return "\n".join(L)


def reorganiza(db, aplica=False):
    """Traz um banco antigo ao modelo: fato é só constatação provada (o resto vira pista, mesmo id e arestas) e
    todo nó citado num passo pertence ao ramo desse passo. Sem `aplica`, só mostra o plano."""
    L = []
    rs = q(db, "SELECT n.*, f.natureza, f.conferido, f.citacao, f.fonte FROM no n JOIN fato f ON f.no=n.id "
               "WHERE n.tipo='fato'")
    # citação com o texto literal gravado e a fonte ligada carrega a própria prova
    literal = {r["id"] for r in rs if r["natureza"] == "citacao" and (r["citacao"] or "").strip() and r["fonte"]}
    vira = [r for r in rs if r["id"] not in literal and (r["natureza"] not in NATUREZAS_FATO or not r["conferido"])]
    por_nat = {}
    for r in vira:
        por_nat[r["natureza"] or "?"] = por_nat.get(r["natureza"] or "?", 0) + 1
    L.append(f"fatos: {len(rs)}; viram pista {len(vira)} (" + ", ".join(f"{k} {v}" for k, v in sorted(por_nat.items()))
             + f"); ficam fato {len(rs) - len(vira)} (provados)")
    ref = {}  # nó citado → primeiro ramo que o cita
    for p in q(db, "SELECT ramo, nos FROM passo WHERE nos IS NOT NULL ORDER BY id"):
        for x in p["nos"].split(","):
            m = re.fullmatch(r"[A-Z](\d+)", x.strip())
            if m:
                ref.setdefault(int(m[1]), p["ramo"])
    sem = [i for i in ref if (um(db, "SELECT ramo FROM no WHERE id=? AND tipo != 'ramo'", i) or {"ramo": 1})["ramo"] is None]
    L.append(f"nós citados em passos: {len(ref)}; ganham ramo {len(sem)}")
    if aplica:
        for r in vira:
            est = "descartada" if r["estado"] in ("retratado", "contestado") else "aberta"
            db.execute("UPDATE no SET tipo='pista', estado=? WHERE id=?", (est, r["id"]))
            motivo = ("não é constatação" if r["natureza"] not in NATUREZAS_FATO else "sem prova registrada")
            evento(db, r["id"], "reclassificado", f"fato→pista ({est}): {r['natureza']}, {motivo}")
            indexa(db, r["id"])
        db.execute("UPDATE fato SET conferido_por='fonte' WHERE conferido IS NOT NULL AND conferido_por IS NULL AND "
                   "no IN (SELECT id FROM no WHERE tipo='fato')")  # o confere antigo era "conferido na fonte"
        for i in literal:
            db.execute("UPDATE fato SET conferido=coalesce(conferido, ?), conferido_por=coalesce(conferido_por, 'fonte') "
                       "WHERE no=?", (agora(), i))
        for i in sem:
            db.execute("UPDATE no SET ramo=? WHERE id=?", (ref[i], i))
            evento(db, i, "religado", f"ramo B{ref[i]}")
    soltos = um(db, "SELECT count(*) FROM no n WHERE n.tipo IN ('fato','pista','hipotese','teste','questao') AND "
                    "n.pai IS NULL AND n.ramo IS NULL AND n.id NOT IN (SELECT de FROM aresta UNION SELECT para FROM aresta)")[0]
    L.append(f"soltos (sem pai, sem ramo, sem aresta): {soltos}")
    L.append("aplicado" if aplica else "plano apenas: `reorganiza --aplica` grava (faça backup do caso.db antes)")
    return "\n".join(L)


def nova_conexao(db, de, para, relacao, porque, rival=None, discriminador=None, origem="agente", motivos=(), canal=None):
    if relacao not in ARESTAS:
        raise Erro(f"relação inválida; use: {', '.join(ARESTAS)}")
    if de["id"] == para["id"]:
        raise Erro("conexão de um item com ele mesmo")
    if not (porque or "").strip():
        raise Erro("conexão sem justificativa: diga por que a relação parece existir")
    igual = um(db, "SELECT c.no, n.estado FROM conexao c JOIN no n ON n.id=c.no WHERE c.relacao=? AND "
                   "((c.de=? AND c.para=?) OR (c.de=? AND c.para=?))", relacao, de["id"], para["id"], para["id"], de["id"])
    if igual:
        raise Erro(f"já registrada: C{igual['no']} ({igual['estado']}); `ver C{igual['no']}`")
    no = cria(db, "conexao", f"{rot(de)} {relacao}? {rot(para)}: {porque}"[:160], resumo=porque[:800], origem=origem)
    db.execute("INSERT INTO conexao VALUES (?,?,?,?,?,?,?)", (no, de["id"], para["id"], relacao, rival, discriminador, canal))
    for m in motivos:
        db.execute("INSERT OR IGNORE INTO aresta VALUES (?,?,?,?,?)", (no, "deriva", pega(db, m)["id"], None, agora()))
    indexa(db, no)
    return no


# ---------- extração: contrato JSON → registro (MODELO.md, "Contrato de extração") ----------

CHAVES_EXTRACAO = {"fonte", "observacoes", "pistas", "interpretacoes", "questoes", "hipoteses", "conexoes",
                   "discriminadores", "impacto"}


def extrai(db, dados, aplica=False, so=None, rejeita=()):
    """Valida o contrato, mostra o plano e, com aplica, grava tudo numa transação (erro em qualquer item
    desfaz o lote inteiro). Ids locais (o1, q1…) viram ids do caso; ids do caso (E42, ext:42) são reusados."""
    extra = set(dados) - CHAVES_EXTRACAO
    if extra:
        raise Erro(f"chave desconhecida no contrato: {', '.join(sorted(extra))} (válidas: {', '.join(sorted(CHAVES_EXTRACAO))})")
    mapa_ids, plano = {}, []
    for chave in CHAVES_EXTRACAO - {"fonte", "impacto"}:
        for d in dados.get(chave, []):
            if re.fullmatch(r"[A-Z]\d+", str(d.get("id", ""))):
                raise Erro(f"id local {d['id']!r} parece id do caso; use minúsculas (o1, q1, h1)")
    usa = lambda loc: (so is None or loc in so) and loc not in rejeita
    existe = lambda ref: bool(re.fullmatch(r"[A-Z]\d+", str(ref))) or ":" in str(ref)

    def ref(x):
        if x in mapa_ids:
            return mapa_ids[x]
        if existe(x):
            return pega(db, x)["id"]
        raise Erro(f"referência {x!r} não existe no caso nem foi criada neste lote (selecionada com --so?)")

    def mesmo(tipo, texto):
        alvo = " ".join(texto.lower().split())[:160]
        return next((r for r in q(db, "SELECT * FROM no WHERE tipo=? AND estado NOT IN ('retratado','rejeitada')", tipo)
                     if " ".join(r["titulo"].lower().split()) == alvo), None)

    fonte = dados.get("fonte")
    fonte_id = rot(pega(db, fonte, "fonte")) if fonte and existe(fonte) else None
    if fonte and not fonte_id:
        raise Erro("fonte: use o id S.. de uma fonte já registrada (`holmes.py fonte <arquivo>` antes)")
    def item(d, k):
        if not d.get(k):
            raise Erro(f"item sem {k!r}: {d}")
        return d[k]

    for o in dados.get("observacoes", []):
        loc = item(o, "id")
        if not usa(loc):
            continue
        if o.get("existente"):
            mapa_ids[loc] = pega(db, o["existente"], ("fato", "pista"))["id"]
            plano.append(f"= {loc} → E{mapa_ids[loc]} (já registrado)")
            continue
        nat = o.get("natureza", "observacao")
        if nat in ("interpretacao", "inferencia"):
            raise Erro(f"{loc}: observação não pode ter natureza {nat}; ponha em 'interpretacoes'")
        r = mesmo("fato", item(o, "texto")) or mesmo("pista", item(o, "texto"))
        if r:
            mapa_ids[loc] = r["id"]
            plano.append(f"= {loc} → {rot(r)} (mesmo texto já registrado; não duplico)")
            continue
        if aplica:
            citacao, local = o.get("citacao"), o.get("local")
            if o.get("pedaco"):  # trecho literal do corpus: copiado, não parafraseado
                with C.conecta() as cdb:
                    p = C.pedaco(cdb, int(o["pedaco"]))
                citacao, local = p["texto"][:1000], local or f"pedaço #{p['id']}"
            origem = o.get("origem", "fonte" if fonte_id or o.get("pedaco") else "medido")
            resumo = " · ".join(x for x in (o.get("metodo") and f"método: {o['metodo']}",
                                             o.get("limites") and f"limites: {o['limites']}") if x) or None
            por = "fonte" if o.get("pedaco") else o.get("por")  # citação literal copiada já está provada
            tipo_o = "fato" if por and nat in NATUREZAS_FATO else "pista"
            no = cria(db, tipo_o, o["texto"], resumo=resumo, origem=origem, grau=o.get("grau"), natureza=nat,
                      fonte=o.get("fonte") or fonte_id, local=local, citacao=citacao, por=por, prova=o.get("prova"))
            mapa_ids[loc] = no
        provada = (o.get("pedaco") or o.get("por")) and nat in NATUREZAS_FATO
        plano.append(f"+ {loc} {'fato' if provada else 'pista'}/{nat}: {o['texto'][:90]}")
    for x in dados.get("questoes", []):
        loc = item(x, "id")
        if not usa(loc):
            continue
        r = mesmo("questao", item(x, "texto"))
        if r:
            mapa_ids[loc] = r["id"]
            plano.append(f"= {loc} → {rot(r)} (questão já registrada)")
            continue
        if aplica:
            pai = x.get("pai") or rot(um(db, "SELECT * FROM no WHERE tipo='objetivo'"))
            mapa_ids[loc] = cria(db, "questao", x["texto"], ref(pai) if pai in mapa_ids else pai, x.get("resumo"))
            for m in x.get("motivada_por", []):
                db.execute("INSERT OR IGNORE INTO aresta VALUES (?,?,?,?,?)", (mapa_ids[loc], "deriva", ref(m), None, agora()))
        plano.append(f"+ {loc} questão: {x['texto'][:90]}")
    for p in dados.get("pistas", []):
        obs = item(p, "obs")
        if not usa(obs):
            continue
        sobre = p.get("sobre") or rot(um(db, "SELECT * FROM no WHERE tipo='objetivo'"))
        if aplica:
            db.execute("INSERT OR IGNORE INTO aresta VALUES (?,?,?,?,?)",
                       (ref(obs), "sobre", ref(sobre), (p.get("porque") or "")[:200] or None, agora()))
        plano.append(f"+ pista {obs} sobre {sobre}: {(p.get('porque') or '')[:80]}")
    for i in dados.get("interpretacoes", []):
        loc = item(i, "id")
        if not usa(loc):
            continue
        if aplica:
            alt = i.get("alternativas")
            resumo = " · ".join(x for x in (alt and f"alternativas: {alt}", i.get("confianca") and f"confiança: {i['confianca']}") if x)
            mapa_ids[loc] = cria(db, "pista", item(i, "texto"), resumo=resumo or None, origem=i.get("origem", "agente"),
                                 natureza="interpretacao")
            if i.get("sobre"):
                db.execute("INSERT OR IGNORE INTO aresta VALUES (?,?,?,?,?)", (mapa_ids[loc], "sobre", ref(i["sobre"]), None, agora()))
        plano.append(f"+ {loc} pista/interpretação (não é fato): {i['texto'][:80]}")
    for h in dados.get("hipoteses", []):
        loc = item(h, "id")
        if not usa(loc):
            continue
        r = mesmo("hipotese", item(h, "texto"))
        if r:
            mapa_ids[loc] = r["id"]
            plano.append(f"= {loc} → {rot(r)} (hipótese já registrada)")
            continue
        if aplica:
            mapa_ids[loc] = cria(db, "hipotese", h["texto"], item(h, "pai"), h.get("resumo"), prob=h.get("prob"),
                                 refuta_se=h.get("refuta_se"))
            for tipo, chave in (("responde", "responde"), ("deriva", "motivada_por"), ("depende", "premissas")):
                vals = h.get(chave) or []
                for v in [vals] if isinstance(vals, str) else vals:
                    db.execute("INSERT OR IGNORE INTO aresta VALUES (?,?,?,?,?)", (mapa_ids[loc], tipo, ref(v), None, agora()))
        plano.append(f"+ {loc} hipótese{'' if h.get('refuta_se') else ' exploratória (sem --refuta-se)'}: {h['texto'][:80]}")
    if aplica:  # rivais depois que todas as hipóteses do lote existem
        for h in dados.get("hipoteses", []):
            if usa(h["id"]):
                for v in h.get("rivais", []):
                    if usa(v) or existe(v):
                        db.execute("INSERT OR IGNORE INTO aresta VALUES (?,?,?,?,?)", (ref(h["id"]), "rival", ref(v), None, agora()))
    for k, c in enumerate(dados.get("conexoes", [])):
        loc = c.get("id", f"c{k + 1}")
        if not usa(loc):
            continue
        if c.get("estado", "sugerida") != "sugerida":
            raise Erro(f"{loc}: conexão de extração entra só como 'sugerida'; confirmar exige `estado C.. confirmada`")
        if aplica:
            no_de = lambda k: um(db, "SELECT * FROM no WHERE id=?", ref(item(c, k)))
            mapa_ids[loc] = nova_conexao(db, no_de("de"), no_de("para"), item(c, "relacao"), item(c, "porque"),
                                         c.get("rival"), c.get("discriminador"), c.get("origem", "agente"),
                                         [str(ref(m)) for m in c.get("motivos", [])], c.get("canal"))
        plano.append(f"+ {loc} conexão candidata {c['de']} {c['relacao']}? {c['para']}: {c['porque'][:70]}")
    for k, d in enumerate(dados.get("discriminadores", [])):
        loc = d.get("id", f"d{k + 1}")
        if not usa(loc):
            continue
        if aplica:
            entre = d.get("entre", [])
            nomes = [rot(um(db, "SELECT * FROM no WHERE id=?", ref(e))) for e in entre]
            no = cria(db, "fio", f"Discriminar {' × '.join(nomes)}: {item(d, 'observacao')}"[:160], resumo=d["observacao"][:800])
            for e in entre:
                db.execute("INSERT OR IGNORE INTO aresta VALUES (?,?,?,?,?)", (no, "sobre", ref(e), None, agora()))
            mapa_ids[loc] = no
        plano.append(f"+ {loc} fio de discriminação: {d['observacao'][:80]}")
    imp = dados.get("impacto") or {}
    for k in ("plano", "leitura"):
        if imp.get(k):
            plano.append(f"! impacto no {k} (não aplicado sozinho): {imp[k][:160]}")
    if aplica:
        for no in set(mapa_ids.values()):
            indexa(db, no)
    return plano, mapa_ids


def roda_prova(cmd):
    try:
        r = subprocess.run(cmd, shell=True, cwd=RAIZ, capture_output=True, text=True, timeout=600)
        return r.returncode == 0, (r.stdout + r.stderr).strip()[-200:]
    except subprocess.TimeoutExpired:
        return False, "timeout de 600 s"


# ---------- CLI ----------

def main(argv=None):
    ap = argparse.ArgumentParser(prog="holmes.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init"); s.add_argument("caso"); s.add_argument("objetivo")
    s = sub.add_parser("usa"); s.add_argument("caso")
    for nome in ("casos", "saude", "jobs", "questoes", "proximo", "cronologia"):
        sub.add_parser(nome)
    s = sub.add_parser("prova"); s.add_argument("--executa", action="store_true"); s.add_argument("--legado", action="store_true")
    s = sub.add_parser("cadeia"); s.add_argument("id")
    s = sub.add_parser("conexoes"); s.add_argument("alvo", nargs="?"); s.add_argument("-n", type=int, default=8)
    s = sub.add_parser("conexao"); s.add_argument("de"); s.add_argument("para"); s.add_argument("relacao", choices=ARESTAS)
    s.add_argument("porque"); s.add_argument("--rival"); s.add_argument("--discriminador"); s.add_argument("--motivos")
    s.add_argument("--origem", default="agente", choices=ORIGENS); s.add_argument("--canal")
    s = sub.add_parser("extrai"); s.add_argument("arquivo"); s.add_argument("--aplica", action="store_true")
    s.add_argument("--so"); s.add_argument("--rejeita")
    s = sub.add_parser("mapa"); s.add_argument("--tudo", action="store_true")
    s = sub.add_parser("novo"); s.add_argument("tipo"); s.add_argument("titulo")
    for k in ("--pai", "--resumo", "--origem", "--grau", "--estado", "--natureza", "--fonte", "--local", "--citacao",
              "--prova", "--refuta-se", "--classe", "--alias", "--proibe", "--permite", "--porque", "--por"):
        s.add_argument(k)
    s.add_argument("--prob", type=float)
    s = sub.add_parser("edita"); s.add_argument("id"); s.add_argument("--titulo"); s.add_argument("--resumo")
    s.add_argument("--refuta-se")
    s = sub.add_parser("leitura"); s.add_argument("texto", nargs="?"); s.add_argument("--titulo")
    for k in ("--sustenta", "--enfraquece", "--rival", "--questao", "--lacuna", "--motivo"):
        s.add_argument(k)
    s = sub.add_parser("estado"); s.add_argument("id"); s.add_argument("estado"); s.add_argument("motivo", nargs="?", default="")
    s.add_argument("--solucao"); s.add_argument("--prova")
    for nome in ("liga", "desliga"):
        s = sub.add_parser(nome); s.add_argument("de"); s.add_argument("tipo", choices=ARESTAS); s.add_argument("para")
        if nome == "liga":
            s.add_argument("nota", nargs="?")
    s = sub.add_parser("prob"); s.add_argument("hipotese"); s.add_argument("p", type=float); s.add_argument("motivo")
    s = sub.add_parser("ach"); s.add_argument("alvo"); s.add_argument("hipotese", nargs="?")
    s.add_argument("valor", nargs="?", choices=list(ACH)); s.add_argument("--nota")
    s = sub.add_parser("teste"); s.add_argument("hipotese"); s.add_argument("titulo")
    s.add_argument("--alcance", required=True); s.add_argument("--porque", required=True)
    for k in ("--fora", "--previsao", "--controle", "--instrumento", "--script", "--resumo"):
        s.add_argument(k)
    s.add_argument("--controle-tipo", choices=["real", "plantado", "sabotagem", "nenhum"])
    s.add_argument("--forca", action="store_true"); s.add_argument("--exploratorio", action="store_true")
    s = sub.add_parser("roda"); s.add_argument("teste"); s.add_argument("--pid", type=int); s.add_argument("--log")
    s.add_argument("--host")
    s = sub.add_parser("resultado"); s.add_argument("alvo")
    s.add_argument("resultado", choices=["positivo", "negativo", "inconclusivo", "falhou"]); s.add_argument("nota")
    s.add_argument("--n"); s.add_argument("--controle-ok", choices=["sim", "nao"]); s.add_argument("--sentido")
    for nome in ("busca", "ja"):
        s = sub.add_parser(nome); s.add_argument("texto"); s.add_argument("-n", type=int, default=8)
        s.add_argument("--sem-corpus", action="store_true")
    s = sub.add_parser("ver"); s.add_argument("id")
    s = sub.add_parser("fonte"); s.add_argument("caminho"); s.add_argument("--titulo")
    s.add_argument("--procedencia", choices=["primaria", "derivada", "terceiros", "nossa"], default="primaria")
    s.add_argument("--confiabilidade", choices=list("ABCDEF")); s.add_argument("--sem-corpus", action="store_true")
    s = sub.add_parser("cita"); s.add_argument("pedaco", type=int); s.add_argument("afirmacao")
    s.add_argument("--natureza", default="citacao", choices=NATUREZAS); s.add_argument("--grau", default="B")
    s = sub.add_parser("confere"); s.add_argument("fato", help="pista K.. (vira fato) ou fato E.. (renova a prova)"); s.add_argument("nota")
    s.add_argument("--por", required=True, choices=PROVAS); s.add_argument("--prova")
    s = sub.add_parser("atributo"); s.add_argument("entidade"); s.add_argument("chave"); s.add_argument("valor")
    s.add_argument("--fato")
    s = sub.add_parser("ramo"); s.add_argument("acao", nargs="?", choices=["novo", "usa", "solta"])
    s.add_argument("texto", nargs="?"); s.add_argument("--de"); s.add_argument("--passo", type=int)
    s.add_argument("--porque"); s.add_argument("--resumo"); s.add_argument("--nao-usa", action="store_true")
    s = sub.add_parser("passo"); s.add_argument("tipo", choices=PASSOS_MANUAIS); s.add_argument("texto")
    s.add_argument("--porque"); s.add_argument("--nos"); s.add_argument("--ramo")
    s = sub.add_parser("arvore"); s.add_argument("id", nargs="?")
    s = sub.add_parser("trilha"); s.add_argument("id", nargs="?")
    sub.add_parser("ficha")
    s = sub.add_parser("reorganiza"); s.add_argument("--aplica", action="store_true")
    s = sub.add_parser("instrumento"); s.add_argument("caminho"); s.add_argument("nome", nargs="?")
    s.add_argument("--verificador")
    a = ap.parse_args(argv)

    if a.cmd == "init":
        if not re.fullmatch(r"[\w-]+", a.caso):
            raise Erro("nome de caso: letras, números, _ e -")
        d = CASOS / a.caso
        if (d / "caso.db").exists():
            raise Erro(f"{a.caso} já existe")
        for sd in ("fontes", "scripts", "saidas", "notas"):
            (d / sd).mkdir(parents=True, exist_ok=True)
        (d / "CASO.md").write_text(f"# {a.caso}\n\nObjetivo: {a.objetivo}\n\n<!-- até 2 KB, à mão: o que é o caso, "
                                   "regras locais, onde ficam as fontes. Estado e plano NÃO vão aqui: são o `mapa`. -->\n",
                                   encoding="utf-8")
        with conecta(a.caso) as db:
            cria(db, "objetivo", a.objetivo[:160], resumo=a.objetivo if len(a.objetivo) > 160 else None, origem="usuario")
        ATIVO.parent.mkdir(exist_ok=True)
        ATIVO.write_text(a.caso)
        return print(f"caso {a.caso} criado em {d} e ativo")
    if a.cmd == "usa":
        if a.caso not in casos():
            raise Erro(f"{a.caso} não existe; casos: {', '.join(casos()) or 'nenhum'}")
        ATIVO.parent.mkdir(exist_ok=True)
        ATIVO.write_text(a.caso)
        return print(f"caso ativo: {a.caso}")
    if a.cmd == "casos":
        atual = ATIVO.read_text().strip() if ATIVO.exists() else ""
        return print("\n".join(f"{'*' if c == atual else ' '} {c}" for c in casos()) or "nenhum caso")

    caso = caso_ativo()
    with conecta(caso) as db:
        ra = ramo_ativo(db, caso)
        ATUAL["ramo"] = ra["id"] if ra else None
        if a.cmd == "mapa":
            txt = mapa(db, caso, a.tudo)
            (CASOS / caso / "MAPA.md").write_text(txt + "\n", encoding="utf-8")  # visão gerada; nunca editar
            print(txt)
        elif a.cmd == "novo":
            if a.tipo == "ramo":
                raise Erro("ramo se abre com `ramo novo \"<pergunta>\" --de <id> --porque \"<por que esta linha>\"`")
            no = cria(db, a.tipo, a.titulo, a.pai, a.resumo, a.origem, a.grau, a.estado, natureza=a.natureza,
                      fonte=a.fonte, local=a.local, citacao=a.citacao, prova=a.prova, prob=a.prob,
                      refuta_se=a.refuta_se, classe=a.classe, alias=a.alias, proibe=a.proibe, permite=a.permite,
                      porque=a.porque, por=a.por)
            print(f"{PREFIXO[a.tipo]}{no}")
            if a.tipo == "hipotese" and not a.refuta_se:
                print("dica: --refuta-se \"<o que a derrubaria>\" deixa a hipótese testável")
        elif a.cmd == "edita":
            r = pega(db, a.id)
            if a.titulo:
                if len(a.titulo) > 160:
                    raise Erro("título máx. 160")
                db.execute("UPDATE no SET titulo=? WHERE id=?", (a.titulo, r["id"]))
            if a.resumo is not None:
                if len(a.resumo) > 800:
                    raise Erro("resumo máx. 800")
                db.execute("UPDATE no SET resumo=? WHERE id=?", (a.resumo, r["id"]))
            if a.refuta_se:
                if r["tipo"] != "hipotese":
                    raise Erro("--refuta-se é de hipótese")
                db.execute("UPDATE hipotese SET refuta_se=? WHERE no=?", (a.refuta_se, r["id"]))
            toca(db, r["id"], "editou", f"antes: {r['titulo']}")
            print(f"{rot(r)} editado")
        elif a.cmd == "leitura":
            atual = leitura_atual(db)
            if not a.texto:
                if not atual:
                    return print("nenhuma leitura de conjunto ainda: `holmes.py leitura \"<o que o caso parece contar>\"`")
                return print(ver(db, atual) + f"\n  {resultados_sem_leitura(db)} resultado(s) desde esta leitura")
            if len(a.texto) > 800:
                raise Erro(f"leitura com {len(a.texto)} caracteres (máx. 800): é o quadro, não o dossiê")
            if atual and not (a.motivo or "").strip():
                raise Erro(f"substituir L{atual['id']} exige --motivo: que evidência ou evento mudou o quadro?")
            ids = lambda s: [pega(db, x.strip()) for x in (s or "").split(",") if x.strip()]
            ligs = ([("depende", e["id"], None, "de") for e in ids(a.sustenta)]
                    + [("enfraquece", e["id"], None, "para") for e in ids(a.enfraquece)]
                    + [("rival", h["id"], None, "de") for h in ids(a.rival)]
                    + [("sobre", x["id"], "decisiva", "de") for x in ids(a.questao)]
                    + [("sobre", x["id"], "lacuna", "de") for x in ids(a.lacuna)])
            titulo = a.titulo or " ".join(a.texto.split())[:157] + ("…" if len(a.texto) > 157 else "")
            no = cria(db, "leitura", titulo[:160], resumo=a.texto, origem="agente")
            for tipo, outro, nota, lado in ligs:  # 'de' = a leitura aponta; 'para' = a evidência aponta para a leitura
                par = (no, tipo, outro) if lado == "de" else (outro, tipo, no)
                db.execute("INSERT OR IGNORE INTO aresta VALUES (?,?,?,?,?)", (*par, nota, agora()))
            if atual:
                db.execute("UPDATE no SET estado='substituida' WHERE id=?", (atual["id"],))
                db.execute("INSERT OR IGNORE INTO aresta VALUES (?,?,?,?,?)", (no, "substitui", atual["id"], a.motivo[:200], agora()))
                toca(db, atual["id"], "substituida", f"L{no}: {a.motivo}")
            print(f"L{no} é a leitura atual" + (f" (substitui L{atual['id']})" if atual else ""))
            if not a.sustenta:
                print("aviso: leitura sem --sustenta: se uma evidência dela cair, ninguém vai avisar")
        elif a.cmd == "estado":
            r = pega(db, a.id)
            if a.estado not in ESTADOS[r["tipo"]]:
                raise Erro(f"estado inválido para {r['tipo']}; use: {', '.join(ESTADOS[r['tipo']])}")
            if a.estado in COM_MOTIVO and not a.motivo.strip():
                raise Erro(f"'{a.estado}' exige motivo (o id do teste, fato ou decisão que mostrou isso)")
            if r["tipo"] == "frente" and a.estado == "ativa" and r["estado"] != "ativa":
                if um(db, "SELECT count(*) FROM no WHERE tipo='frente' AND estado='ativa'")[0] >= MAX_FRENTES:
                    raise Erro(f"já há {MAX_FRENTES} frentes ativas")
            if r["tipo"] == "hipotese" and a.estado == "refutada":
                h = um(db, "SELECT refuta_se FROM hipotese WHERE no=?", r["id"])
                print(f"lembrete: refute {rot(r)} só se o critério foi atingido: "
                      f"{h['refuta_se'] or '(nenhum critério registrado)'}. Se não foi, mas negativos válidos se "
                      "acumulam, baixe a confiança com `prob` em vez de mantê-la intacta.")
            if r["tipo"] == "conexao" and a.estado == "confirmada":
                c = um(db, "SELECT * FROM conexao WHERE no=?", r["id"])
                db.execute("INSERT OR IGNORE INTO aresta VALUES (?,?,?,?,?)",
                           (c["de"], c["relacao"], c["para"], f"C{r['id']}: {a.motivo}"[:200], agora()))
                print(f"relação promovida ao grafo: {rot(um(db, 'SELECT * FROM no WHERE id=?', c['de']))} {c['relacao']} "
                      f"{rot(um(db, 'SELECT * FROM no WHERE id=?', c['para']))}")
            if r["tipo"] == "conexao" and r["estado"] == "confirmada" and a.estado != "confirmada":
                c = um(db, "SELECT * FROM conexao WHERE no=?", r["id"])
                db.execute("DELETE FROM aresta WHERE de=? AND tipo=? AND para=? AND nota LIKE ?",
                           (c["de"], c["relacao"], c["para"], f"C{r['id']}:%"))
            if r["tipo"] == "alvo" and a.estado == "resolvido":
                if not a.solucao:
                    raise Erro("alvo resolvido exige --solucao (e, se houver, --prova \"<comando que re-prova>\")")
                db.execute("UPDATE alvo SET solucao=?, prova=? WHERE no=?", (a.solucao, a.prova, r["id"]))
            db.execute("UPDATE no SET estado=? WHERE id=?", (a.estado, r["id"]))
            toca(db, r["id"], f"{r['estado']}→{a.estado}", a.motivo)
            onde = r["id"] if r["tipo"] == "ramo" else ATUAL["ramo"]
            if onde:  # correção de rumo fica no percurso, com o porquê
                passo(db, onde, "mudou", f"{rot(r)} {r['estado']} → {a.estado}", a.motivo.strip() or None, (rot(r),))
            if r["tipo"] == "ramo" and a.estado != "ativo" and ATUAL["ramo"] == r["id"]:
                arq_ramo(caso).unlink(missing_ok=True)
                print("ramo ativo solto: `arvore` mostra os outros; `ramo usa B..` escolhe")
            print(f"{rot(r)}: {r['estado']} → {a.estado}")
            dep = dependentes(db, r["id"])
            if a.estado in CAIDOS and dep:
                print("⚠ dependem disto (direta ou indiretamente) e precisam ser reavaliados: "
                      + ", ".join(rot(um(db, "SELECT * FROM no WHERE id=?", d)) for d in dep[:20])
                      + (f" … +{len(dep) - 20}" if len(dep) > 20 else ""))
        elif a.cmd in ("liga", "desliga"):
            de, para = pega(db, a.de), pega(db, a.para)
            if de["id"] == para["id"]:
                raise Erro("aresta para si mesmo")
            if a.cmd == "liga":
                db.execute("INSERT OR IGNORE INTO aresta VALUES (?,?,?,?,?)", (de["id"], a.tipo, para["id"], a.nota, agora()))
            else:
                db.execute("DELETE FROM aresta WHERE de=? AND tipo=? AND para=?", (de["id"], a.tipo, para["id"]))
            evento(db, de["id"], f"{a.cmd} {a.tipo}", rot(para))
            print(f"{rot(de)} {a.tipo} {rot(para)}" + (" (desfeita)" if a.cmd == "desliga" else ""))
        elif a.cmd == "prob":
            h = pega(db, a.hipotese, "hipotese")
            if not 0 <= a.p <= 1:
                raise Erro("probabilidade entre 0 e 1")
            velho = um(db, "SELECT prob FROM hipotese WHERE no=?", h["id"])["prob"]
            db.execute("UPDATE hipotese SET prob=? WHERE no=?", (a.p, h["id"]))
            toca(db, h["id"], f"prob {velho}→{a.p}", a.motivo)
            irmas = q(db, "SELECT h.prob FROM no n JOIN hipotese h ON h.no=n.id WHERE n.pai=? AND n.estado IN "
                          "('viva','apoiada') AND h.prob IS NOT NULL", h["pai"])
            s = sum(x["prob"] for x in irmas)
            # somar 1 só se exige de rivais mutuamente exclusivas; explicações que coexistem podem passar de 1
            print(f"{rot(h)} p={a.p}" + (f"  (hipóteses vivas da frente somam {s:.2f}: se forem rivais exclusivas, "
                                         "passa de 1 e precisa de ajuste; se podem ser verdade juntas, ignore)"
                                         if s > 1.05 and len(irmas) > 1 else ""))
        elif a.cmd == "ach":
            alvo = pega(db, a.alvo)
            if alvo["tipo"] == "frente" and not a.hipotese:
                print(matriz_ach(db, alvo))
            else:
                if not (a.hipotese and a.valor):
                    raise Erro("uso: ach <E> <H> CC|C|N|I|II   ou   ach <F>")
                e, h = pega(db, a.alvo, ("fato", "pista")), pega(db, a.hipotese, "hipotese")
                db.execute("INSERT OR REPLACE INTO ach VALUES (?,?,?,?)", (e["id"], h["id"], a.valor, a.nota))
                evento(db, h["id"], f"ach {a.valor}", rot(e))
                print(f"{rot(e)} × {rot(h)} = {a.valor}")
        elif a.cmd == "teste":
            h = pega(db, a.hipotese, "hipotese")
            if h["estado"] not in ("viva", "apoiada"):
                raise Erro(f"{rot(h)} está {h['estado']}: reabra antes de testar")
            if not a.exploratorio and not um(db, "SELECT refuta_se FROM hipotese WHERE no=?", h["id"])["refuta_se"]:
                raise Erro(f"{rot(h)} não diz o que a derrubaria. Antes de testar: `holmes.py edita {rot(h)} --refuta-se "
                           "\"<observação que a refutaria>\"`. Sem isso, nenhum resultado pesa contra ela. Para só "
                           "explorar um palpite barato, use --exploratorio (vale como pista, não como cobertura).")
            receita = hashlib.sha256(" ".join(re.findall(r"\w+", (a.titulo + " " + a.alcance).lower())).encode()).hexdigest()[:16]
            igual = um(db, "SELECT t.no FROM teste t JOIN no n ON n.id=t.no WHERE t.receita=? AND n.estado != 'cancelado' "
                           "AND coalesce(t.modo, '') = ?", receita, "exploratorio" if a.exploratorio else "")
            if igual and not a.forca:
                raise Erro(f"já existe T{igual['no']} com o mesmo título+alcance (`ver T{igual['no']}`; "
                           f"para repetir após consertar o instrumento use `roda T{igual['no']}`; --forca cria outro)")
            parecidos = busca(db, a.titulo + " " + a.alcance, 3, so_testes=True)
            inst = pega(db, a.instrumento, "instrumento") if a.instrumento else None
            no = cria(db, "teste", a.titulo, h["id"], a.resumo, "agente", porque=a.porque)
            db.execute("INSERT INTO teste(no, alcance, fora, porque, previsao, previsao_em, controle, controle_tipo, "
                       "instrumento, script, receita, modo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                       (no, a.alcance, a.fora, a.porque, a.previsao, agora() if a.previsao else None, a.controle,
                        a.controle_tipo or ("nenhum" if not a.controle else None), inst["id"] if inst else None,
                        a.script, receita, "exploratorio" if a.exploratorio else None))
            indexa(db, no)
            print(f"T{no}")
            if a.exploratorio:
                print("exploratório: o resultado vale como pista. Não confirma previsão nem fecha alcance; se render "
                      "algo, registre a ideia como hipótese e faça o teste confirmatório depois.")
            if parecidos:
                print("parecidos já registrados (confira se não é repetição):\n  " + "\n  ".join(parecidos))
            if not inst:
                print("aviso: sem --instrumento, um negativo vale INDETERMINADO")
            if not a.controle_tipo or a.controle_tipo in ("nenhum", "plantado"):
                print("aviso: sem controle real (dado conhecido que o instrumento precisa reconhecer)")
        elif a.cmd == "roda":
            t = pega(db, a.teste, "teste")
            print(f"X{abre_execucao(db, t, a.pid, a.log, a.host)}")
        elif a.cmd == "resultado":
            if a.alvo.startswith("X"):
                x = um(db, "SELECT * FROM execucao WHERE id=?", int(a.alvo[1:]))
                if not x:
                    raise Erro(f"{a.alvo} não existe")
                t = pega(db, x["teste"])
            else:
                t = pega(db, a.alvo, "teste")
                x = um(db, "SELECT * FROM execucao WHERE teste=? AND resultado IS NULL ORDER BY id DESC", t["id"])
                if not x:  # tentativa rápida: abre e fecha a execução de uma vez
                    x = um(db, "SELECT * FROM execucao WHERE id=?", abre_execucao(db, t))
            sentido = " ".join((a.sentido or "").split()) or None
            if sentido:  # quatro estados: substantivo · "nenhum: <por quê>" · "revisar: <o quê>" · ausente = pendente
                pref, _, resto = sentido.partition(":")
                pref = pref.strip().lower()
                if pref in ("nenhum", "revisar"):
                    sentido = f"{pref}:{resto}"
                    if len(resto.strip()) < 8:
                        raise Erro(f"--sentido \"{pref}: ...\" precisa dizer {'por que não há sentido legível' if pref == 'nenhum' else 'o que rever'}")
                elif len(sentido) < 15:
                    raise Erro("--sentido curto demais para dizer algo. Escreva o que a saída diz no contexto, ou "
                               "\"nenhum: <por quê>\", ou \"revisar: <o quê>\", ou omita (fica pendente para a leitura de conjunto)")
            ok = {"sim": 1, "nao": 0}.get(a.controle_ok)
            db.execute("UPDATE execucao SET resultado=?, nota=?, n=?, controle_ok=?, fim=?, sentido=? WHERE id=?",
                       (a.resultado, a.nota, a.n, ok, agora(), sentido, x["id"]))
            aberta = um(db, "SELECT 1 FROM execucao WHERE teste=? AND resultado IS NULL", t["id"])
            db.execute("UPDATE no SET estado=? WHERE id=?", ("rodando" if aberta else "feito", t["id"]))
            toca(db, t["id"], f"X{x['id']} {a.resultado}", a.nota)
            if ATUAL["ramo"]:
                passo(db, ATUAL["ramo"], "testou", f"{rot(t)} X{x['id']} → {a.resultado}: {t['titulo']}",
                      (a.sentido or a.nota or "")[:400] or None, (rot(t),))
            v = validade(db, t["id"])
            print(f"{rot(t)} X{x['id']} → {a.resultado}" + (f" ⚠ {v}" if v else ""))
            print("Diga ao usuário em uma linha o que isto muda no plano (ACHADO / NEGATIVO no alcance / CONTROLE / "
                  "INSTRUMENTO) e o que significa.")
            if a.resultado == "negativo":
                print("Um negativo fecha esta forma no alcance testado, não o conceito inteiro; negativos válidos que "
                      "se acumulam devem baixar a confiança (`prob`).")
            if not sentido and a.resultado != "falhou":
                print("sentido pendente: será lido na leitura de conjunto (ou registre --sentido agora, se a saída "
                      "disser algo como texto ou forma).")
            n, v = tunel(db, pega(db, t["pai"])["pai"])
            if a.resultado == "negativo" and n >= TUNEL:
                print(f"⚠ TÚNEL: {aviso_tunel(n, v)}. Pare e mude para LEITURA antes do próximo teste.")
            lida = pede_leitura(db)
            if lida:
                print("⚠ " + lida)
        elif a.cmd in ("busca", "ja"):
            r = busca(db, a.texto, a.n, so_testes=a.cmd == "ja", com_corpus=not a.sem_corpus)
            print("\n".join(r) if r else "nada registrado com esses termos. Tente sinônimos e `corpus.py busca --modo "
                                         "literal` antes de concluir que é novo: ausência na busca não prova ausência.")
        elif a.cmd == "ver":
            r = pega(db, a.id)
            print(ver(db, r) + ("\n" + trilha(db, r, curto=True) if r["tipo"] == "ramo" else ""))
        elif a.cmd == "ramo":
            if a.acao == "novo":
                if not a.texto or not a.de or not (a.porque or "").strip():
                    raise Erro('uso: ramo novo "<pergunta da linha>" --de <id de onde nasce> --porque "<por que abrir>"'
                               " [--passo N, se nasce de um passo de outro ramo]")
                origem, dp = pega(db, a.de), None
                if a.passo is not None:
                    if origem["tipo"] != "ramo":
                        raise Erro("--passo só vale com --de B..")
                    ps = passos_de(db, origem["id"])
                    if not 1 <= a.passo <= len(ps):
                        raise Erro(f"{rot(origem)} tem {len(ps)} passos")
                    dp = ps[a.passo - 1]["id"]
                ATUAL["ramo"] = None  # abrir um ramo não é passo do ramo que estava ativo
                no = cria(db, "ramo", a.texto, origem["id"], a.resumo, de_passo=dp)
                passo(db, no, "abriu", f"nasce de {rot(origem)}" + (f" (passo {a.passo})" if dp else "")
                      + f": {origem['titulo'][:200]}", a.porque.strip())
                if origem["tipo"] == "ramo":
                    passo(db, origem["id"], "bifurcou", f"→ B{no} {a.texto}", a.porque.strip(), (f"B{no}",))
                if not a.nao_usa:
                    arq_ramo(caso).parent.mkdir(exist_ok=True)
                    arq_ramo(caso).write_text(str(no))
                print(f"B{no}" + ("" if a.nao_usa else " (ativo)"))
            elif a.acao == "usa":
                r = pega(db, a.texto or "", "ramo")
                if r["estado"] != "ativo":
                    raise Erro(f"{rot(r)} está {r['estado']}: `estado {rot(r)} ativo` antes de usar")
                arq_ramo(caso).parent.mkdir(exist_ok=True)
                arq_ramo(caso).write_text(str(r["id"]))
                print(f"ramo ativo: {rot(r)}\n" + trilha(db, r, curto=True))
            elif a.acao == "solta":
                arq_ramo(caso).unlink(missing_ok=True)
                print("nenhum ramo ativo")
            else:
                print(trilha(db, ra, curto=True) if ra else "nenhum ramo ativo (`arvore`, `ramo usa B..`)")
        elif a.cmd == "passo":
            r = pega(db, a.ramo, "ramo") if a.ramo else ra
            if not r:
                raise Erro("nenhum ramo ativo: `ramo usa B..` ou --ramo B..")
            if not (a.porque or "").strip():
                raise Erro("passo sem --porque não reconstrói o raciocínio: diga o que levou a ele")
            nos = tuple(rot(pega(db, x.strip())) for x in (a.nos or "").split(",") if x.strip())
            passo(db, r["id"], a.tipo, a.texto, a.porque.strip(), nos)
            print(f"{rot(r)} passo {len(passos_de(db, r['id']))}")
        elif a.cmd == "arvore":
            print(arvore(db, caso, a.id))
        elif a.cmd == "trilha":
            r = pega(db, a.id, "ramo") if a.id else ra
            print(trilha(db, r) if r else "nenhum ramo ativo: `trilha B..`")
        elif a.cmd == "ficha":
            print(ficha(db, caso))
        elif a.cmd == "reorganiza":
            print(reorganiza(db, a.aplica))
        elif a.cmd == "saude":
            print(saude(db))
        elif a.cmd == "cadeia":
            print("\n".join(cadeia(db, pega(db, a.id))))
        elif a.cmd == "questoes":
            print(questoes(db))
        elif a.cmd == "cronologia":
            print(cronologia(db))
        elif a.cmd == "proximo":
            for i, (acao, porque) in enumerate(proximo(db), 1):
                print(f"{i}. {acao}\n   porque: {porque}")
        elif a.cmd == "conexoes":
            if not a.alvo:
                cs = q(db, "SELECT * FROM no WHERE tipo='conexao' AND estado='sugerida' ORDER BY id")
                return print("\n".join(linha(db, c) for c in cs) or "nenhuma conexão candidata por avaliar")
            alvo = pega(db, a.alvo) if re.fullmatch(r"[A-Z]?\d+|\w+:\w+", a.alvo) else None
            saida, rodape = candidatas(db, texto_de(db, alvo) if alvo else a.alvo, alvo["id"] if alvo else None, a.n)
            print(f"candidatas para {rot(alvo) if alvo else repr(a.alvo)} (consulta; nada foi gravado):")
            print("\n".join(saida + rodape) if saida else "  nenhuma: ausência de conexão também é resultado. Para o que "
                  "não compartilha palavra, descreva o conceito abstrato em texto (`conexoes \"dualidade metades\"`) ou "
                  "registre-o como entidade com aliases.")
            if saida:
                print("Candidata não é relação. Para cada uma: que relação seria, que explicação rival (acaso, mesma "
                      "fonte repetida, tema genérico) e que observação separaria. Grave só a promissora com `conexao`.")
        elif a.cmd == "conexao":
            no = nova_conexao(db, pega(db, a.de), pega(db, a.para), a.relacao, a.porque, a.rival, a.discriminador,
                              a.origem, [m.strip() for m in (a.motivos or "").split(",") if m.strip()], a.canal)
            print(f"C{no} (sugerida: não é aresta do grafo até `estado C{no} confirmada \"<evidência>\"`)")
            if not a.rival:
                print("aviso: sem --rival. Qual seria a explicação sem relação (acaso, tema genérico, mesma fonte)?")
        elif a.cmd == "extrai":
            import json
            try:
                dados = json.loads(Path(a.arquivo).read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                raise Erro(f"contrato ilegível: {e}")
            lista = lambda s: {x.strip() for x in (s or "").split(",") if x.strip()}
            if not isinstance(dados, dict):
                raise Erro("contrato: o JSON precisa ser um objeto com as chaves de MODELO.md")
            try:
                plano, ids = extrai(db, dados, a.aplica, lista(a.so) or None, lista(a.rejeita))
            except (KeyError, TypeError, ValueError, AttributeError) as e:  # erro aqui desfaz o lote inteiro
                raise Erro(f"contrato inválido ({type(e).__name__}: {e}); nada foi gravado")
            print("\n".join(plano) or "nada a extrair")
            if a.aplica:
                print("gravado: " + ", ".join(f"{k}→{rot(um(db, 'SELECT * FROM no WHERE id=?', v))}" for k, v in ids.items()))
            else:
                print("(plano apenas; nada gravado. `--aplica` grava tudo numa transação; `--so`/`--rejeita` escolhem itens)")
        elif a.cmd == "jobs":
            rs = q(db, "SELECT x.*, n.titulo FROM execucao x JOIN no n ON n.id=x.teste WHERE x.resultado IS NULL")
            for x in rs:
                print(f"X{x['id']} (T{x['teste']}) pid {x['pid']} {'vivo' if vivo(x['pid']) else 'MORTO: registre'} "
                      f"log {x['log']}: {x['titulo']}")
            print("" if rs else "nenhuma execução aberta")
        elif a.cmd == "fonte":
            alvo = a.caminho
            local = Path(alvo).exists()
            ref = str(Path(alvo).resolve()) if local else alvo
            r = um(db, "SELECT * FROM fonte WHERE ref=?", ref)
            sha = sha_arquivo(ref) if local else None
            if r:
                no = r["no"]
                if sha and sha != r["sha"]:
                    db.execute("UPDATE fonte SET sha=? WHERE no=?", (sha, no))
                    toca(db, no, "nova versão", f"{(r['sha'] or '')[:12]} → {sha[:12]}")
            else:
                no = cria(db, "fonte", (a.titulo or Path(alvo).name or alvo)[:160], resumo=ref[:800], origem="fonte",
                          estado="catalogada")
                db.execute("INSERT INTO fonte(no, ref, sha, procedencia, confiabilidade) VALUES (?,?,?,?,?)",
                           (no, ref, sha, a.procedencia, a.confiabilidade))
            print(f"S{no} {ref}")
            if local and not a.sem_corpus:
                with C.conecta() as cdb:
                    for did, st, p in C.add(cdb, caso, ref):
                        print(f"  corpus doc {did} {st}: {p}")
                        db.execute("UPDATE fonte SET documento=? WHERE no=?", (did, no)) if Path(ref).is_file() else None
                db.execute("UPDATE no SET estado='indexada' WHERE id=?", (no,))
        elif a.cmd == "cita":
            with C.conecta() as cdb:
                p = C.pedaco(cdb, a.pedaco)
            ref = p["ref"]
            f = um(db, "SELECT * FROM fonte WHERE ref=?", ref)
            fno = f["no"] if f else None
            if not fno:
                fno = cria(db, "fonte", p["titulo"][:160], resumo=ref[:800], origem="fonte", estado="indexada")
                db.execute("INSERT INTO fonte(no, ref, procedencia, documento) VALUES (?,?,?,?)",
                           (fno, ref, "primaria", p["documento"]))
            local = f"pedaço #{p['id']} " + (f"msg {p['msg_id']}" if p["msg_id"] else f"{p['kind']} {p['ordem']}")
            nat = a.natureza if a.natureza in NATUREZAS_FATO else "citacao"
            no = cria(db, "fato", a.afirmacao, origem="fonte", grau=a.grau, natureza=nat, por="fonte",
                      fonte=f"S{fno}", local=local, citacao=p["texto"][:1000])
            print(f"E{no} (citação literal copiada do corpus, conferida agora)")
        elif a.cmd == "confere":
            e = pega(db, a.fato, ("fato", "pista"))
            nat = um(db, "SELECT natureza FROM fato WHERE no=?", e["id"])["natureza"]
            if nat in ("inferencia", "interpretacao"):
                raise Erro(f"{rot(e)} é {nat}: não vira fato. Fato é constatação provada; o que sustenta uma {nat} é "
                           f"outro fato (`novo fato .. --por ..` e `liga E<novo> sustenta {rot(e)}`), e se ela explica "
                           "algo testável, é hipótese")
            por, prova = prova_de(db, a.por, a.prova)
            if nat not in NATUREZAS_FATO:  # relato provado: vale o que foi constatado, não quem contou
                nat = "citacao" if por == "fonte" else "observacao"
            db.execute("UPDATE fato SET natureza=?, conferido=?, conferido_por=?, prova=coalesce(?, prova) WHERE no=?",
                       (nat, agora(), por, prova, e["id"]))
            era = e["tipo"]
            db.execute("UPDATE no SET tipo='fato', estado='vigente' WHERE id=?", (e["id"],))
            toca(db, e["id"], f"provado por {por}", f"{a.nota}" + (f" · prova: {prova}" if prova else ""))
            print(f"E{e['id']} provado por {por}" + (f" (era a pista K{e['id']}; agora é fato)" if era == "pista" else ""))
        elif a.cmd == "atributo":
            n = pega(db, a.entidade, "entidade")
            fato = pega(db, a.fato, "fato")["id"] if a.fato else None
            velho = um(db, "SELECT valor FROM atributo WHERE entidade=? AND chave=?", n["id"], a.chave)
            db.execute("INSERT OR REPLACE INTO atributo VALUES (?,?,?,?,?)", (n["id"], a.chave, a.valor, fato, agora()))
            toca(db, n["id"], f"atributo {a.chave}", f"{velho['valor'] if velho else '∅'} → {a.valor}")
            print(f"{rot(n)}.{a.chave} = {a.valor}" + ("" if fato else "  (sem --fato: de onde vem este valor?)"))
        elif a.cmd == "instrumento":
            ref = a.caminho
            if re.fullmatch(r"I?\d+", ref) and not Path(ref).exists():
                raise Erro("para registrar passe o caminho do arquivo; para verificar use `prova`")
            p = str(Path(ref).resolve())
            s = sha_arquivo(p)
            if not s:
                raise Erro(f"{p} não é arquivo")
            r = um(db, "SELECT * FROM instrumento WHERE caminho=?", p)
            if not r:
                no = cria(db, "instrumento", a.nome or Path(p).name, resumo=p, origem="medido")
                db.execute("INSERT INTO instrumento VALUES (?,?,?)", (no, p, a.verificador))
                db.execute("INSERT INTO versao(instrumento, sha, quando) VALUES (?,?,?)", (no, s, agora()))
                print(f"I{no} registrado ({s[:12]})")
            else:
                no = r["no"]
                if a.verificador:
                    db.execute("UPDATE instrumento SET verificador=? WHERE no=?", (a.verificador, no))
                v = versao_atual(db, no)
                if v["sha"] == s:
                    print(f"I{no} sem mudança ({s[:12]})")
                else:
                    db.execute("INSERT INTO versao(instrumento, sha, quando) VALUES (?,?,?)", (no, s, agora()))
                    toca(db, no, "nova versão", f"{v['sha'][:12]} → {s[:12]}")
                    n = sum(1 for t in q(db, "SELECT no FROM teste WHERE instrumento=?", no)
                            if validade(db, t["no"]).startswith("A REVALIDAR"))
                    print(f"I{no} mudou ({v['sha'][:12]} → {s[:12]}): {n} negativo(s) ficam A REVALIDAR")
        elif a.cmd == "prova":
            leg = "" if a.legado else " AND n.legado=0"
            itens = [(f"E{r['no']}", r["prova"], "fato") for r in q(db, "SELECT f.* FROM fato f JOIN no n ON n.id=f.no AND n.tipo='fato' AND coalesce(f.conferido_por, 'medicao') = 'medicao' "
                                                                      f"WHERE trim(coalesce(f.prova, '')) != ''{leg}")]
            itens += [(f"A{r['no']}", r["prova"], "alvo") for r in q(db, "SELECT x.* FROM alvo x JOIN no n ON n.id=x.no "
                                                                       f"WHERE trim(coalesce(x.prova, '')) != ''{leg}")]
            itens += [(f"I{r['no']}", r["verificador"], "instrumento")
                      for r in q(db, f"SELECT i.* FROM instrumento i JOIN no n ON n.id=i.no WHERE trim(coalesce(i.verificador, '')) != ''{leg}")]
            if not itens:
                print("nenhuma prova registrada (--prova em fato/alvo, --verificador em instrumento)"
                      + ("" if a.legado else "; herdadas só com --legado"))
            if itens and not a.executa:  # são comandos de shell vindos do banco: quem roda tem de ver antes
                print("\n".join(f"  {rid} ({tipo}): {cmd}" for rid, cmd, tipo in itens))
                return print("(listadas, não executadas: confira cada comando e rode `prova --executa`)")
            for rid, cmd, tipo in itens:
                ok, out = roda_prova(cmd)
                print(f"{'OK  ' if ok else 'FALHOU'} {rid} ({tipo}): {cmd}" + ("" if ok else f"\n      {out}"))
                no = int(rid[1:])
                if tipo == "instrumento":
                    db.execute("UPDATE versao SET verificado=? WHERE id=?", (int(ok), versao_atual(db, no)["id"]))
                evento(db, no, "prova " + ("ok" if ok else "FALHOU"), cmd)


if __name__ == "__main__":
    try:
        main()
    except (Erro, C.Erro) as e:
        sys.exit(f"holmes: {e}")
    except sqlite3.IntegrityError as e:
        sys.exit(f"holmes: valor recusado pelo banco ({e})")
