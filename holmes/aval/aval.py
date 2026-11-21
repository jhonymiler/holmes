#!/usr/bin/env python3
"""Avaliação do holmes com um caso sintético de gabarito conhecido (padrão: aval/relojoeiro.json).

  python3 -I holmes/aval/aval.py recuperacao [gabarito]      mede o MECANISMO de descoberta, sem modelo
  python3 -I holmes/aval/aval.py pontua <caso.db> [gabarito] pontua uma investigação feita por um agente

`recuperacao` registra as pistas num caso temporário e mede, para cada ligação verdadeira e cada armadilha,
se o par aparece entre os 5 primeiros de: (a) `busca` (o que existia antes), (b) `conexoes` sem conceitos,
(c) `conexoes` depois de registrar os conceitos que um intérprete proporia. (c) é teto do mecanismo, não do
agente: os conceitos vêm do gabarito. Quem decide se a candidata é relação continua sendo o agente.

`pontua` não precisa do gabarito no caso: casa cada pista com o fato de texto mais parecido e conta ligações
confirmadas (verdadeiras e falsas), armadilhas rejeitadas, questões, revisões da leitura e testes gastos.
O protocolo de uma rodada real com modelo está em aval/README.md; ela não roda aqui.
"""
import json
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
TOP = 5


def carrega(g):
    return json.loads(Path(g or AQUI / "relojoeiro.json").read_text(encoding="utf-8"))


def ids_de(linhas):
    return [int(m[2]) for l in linhas for m in [re.match(r"\s*(?:material )?✗? ?([A-Z])(\d+) \[", l)] if m]


def recuperacao(g):
    raiz = tempfile.mkdtemp()  # caso descartável; o holmes lê o ambiente ao importar
    os.environ.update(HOLMES_RAIZ=raiz, HOLMES_CASOS=f"{raiz}/casos", HOLMES_CORPUS=f"{raiz}/corpus/corpus.db")
    os.environ.pop("HOLMES_CASO", None)
    sys.path.insert(0, str(AQUI.parent))
    import holmes as H
    H.main(["init", g["caso"], g["objetivo"]])
    no = {}
    with H.conecta(g["caso"]) as db:
        for p in g["pistas"]:
            no[p["id"]] = H.cria(db, "fato", p["texto"], natureza="observacao", origem="fonte", por="fonte")
        txt = {k: H.texto_de(db, H.um(db, "SELECT * FROM no WHERE id=?", v)) for k, v in no.items()}
        modos = {
            "busca (antes)": lambda k: [i for i in ids_de(H.busca(db, txt[k], TOP + 1, com_corpus=False)) if i != no[k]][:TOP],
            "conexoes": lambda k: ids_de(H.candidatas(db, txt[k], no[k], TOP)[0]),
        }
        res = {m: medir(g, no, f) for m, f in modos.items()}
        for c in g["conceitos_do_interprete"]:
            H.cria(db, "entidade", c["nome"], classe="conceito", alias=c["aliases"])
        res["conexoes + conceitos"] = medir(g, no, modos["conexoes"])
    return res


def medir(g, no, top):
    achou = lambda a, b: no[b] in top(a) or no[a] in top(b)
    lig = g["ligacoes"]
    r = {"ligacoes": sum(achou(l["de"], l["para"]) for l in lig), "de": len(lig),
         "nao_literais": sum(achou(l["de"], l["para"]) for l in lig if not l["literal"]),
         "de_nao_literais": sum(1 for l in lig if not l["literal"]),
         "armadilhas_na_lista": sum(achou(a["de"], a["para"]) for a in g["armadilhas"]), "de_armadilhas": len(g["armadilhas"])}
    return r


def palavras(t):
    return {w for w in re.findall(r"\w{4,}", t.lower())}


def pontua(caminho, g):
    db = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    fatos = db.execute("SELECT n.id, n.titulo || ' ' || coalesce(f.citacao,'') t FROM no n JOIN fato f ON f.no=n.id "
                       "WHERE f.natureza IN ('observacao','medicao','citacao')").fetchall()
    casa = {}
    for p in g["pistas"]:
        w = palavras(p["texto"])
        melhor = max(((len(w & palavras(f["t"])) / len(w | palavras(f["t"]) or {1}), f["id"]) for f in fatos), default=(0, None))
        if melhor[0] >= 0.5:
            casa[p["id"]] = melhor[1]
    ligados = lambda a, b: a in casa and b in casa and db.execute(
        "SELECT 1 FROM aresta WHERE (de=? AND para=?) OR (de=? AND para=?) UNION SELECT 1 FROM conexao c JOIN no n ON "
        "n.id=c.no WHERE n.estado='confirmada' AND ((c.de=? AND c.para=?) OR (c.de=? AND c.para=?))",
        (casa[a], casa[b], casa[b], casa[a]) * 2).fetchone() is not None
    rejeitou = lambda a, b: a in casa and b in casa and db.execute(
        "SELECT 1 FROM conexao c JOIN no n ON n.id=c.no WHERE n.estado='rejeitada' AND ((c.de=? AND c.para=?) OR "
        "(c.de=? AND c.para=?))", (casa[a], casa[b], casa[b], casa[a])).fetchone() is not None
    conta = lambda sql: db.execute(sql).fetchone()[0]
    leitura = db.execute("SELECT resumo FROM no WHERE tipo='leitura' AND estado='vigente' ORDER BY id DESC").fetchone()
    return {
        "pistas_registradas": f"{len(casa)}/{len(g['pistas'])}",
        "ligacoes_verdadeiras_no_grafo": f"{sum(ligados(l['de'], l['para']) for l in g['ligacoes'])}/{len(g['ligacoes'])}",
        "armadilhas_aceitas_no_grafo (falso positivo)": sum(ligados(a["de"], a["para"]) for a in g["armadilhas"]),
        "armadilhas_rejeitadas_explicitamente": sum(rejeitou(a["de"], a["para"]) for a in g["armadilhas"]),
        "conexoes_sugeridas_sem_decisao": conta("SELECT count(*) FROM no WHERE tipo='conexao' AND estado='sugerida'"),
        "interpretacoes_como_observacao (erro)": conta("SELECT count(*) FROM no n JOIN fato f ON f.no=n.id WHERE "
                                                       "f.natureza='observacao' AND n.origem='agente'"),
        "questoes": conta("SELECT count(*) FROM no WHERE tipo='questao'"),
        "hipoteses": conta("SELECT count(*) FROM no WHERE tipo='hipotese'"),
        "hipoteses_sem_refuta_se": conta("SELECT count(*) FROM hipotese WHERE refuta_se IS NULL"),
        "revisoes_da_leitura": conta("SELECT count(*) FROM no WHERE tipo='leitura'"),
        "leitura_final_contem_solucao": bool(leitura) and any(p.lower() in (leitura["resumo"] or "").lower()
                                                             for p in g["palavras_da_solucao"]),
        "testes_gastos": conta("SELECT count(*) FROM no WHERE tipo='teste'"),
    }


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("recuperacao", "pontua"):
        sys.exit(__doc__)
    if a[0] == "recuperacao":
        for modo, r in recuperacao(carrega(a[1] if len(a) > 1 else None)).items():
            print(f"{modo:22} ligações {r['ligacoes']}/{r['de']} (não literais {r['nao_literais']}/{r['de_nao_literais']})"
                  f" · armadilhas na lista {r['armadilhas_na_lista']}/{r['de_armadilhas']}  [top {TOP}]")
    else:
        print(json.dumps(pontua(a[1], carrega(a[2] if len(a) > 2 else None)), ensure_ascii=False, indent=2))
