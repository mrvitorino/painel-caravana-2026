#!/usr/bin/env python3
"""Gera a versão reduzida (publicada) do Painel de Execução a partir da versão completa.

Entrada : _completo/formacoes-completo.html  (5 abas, JSON completo embutido)
Saída   : formacoes.html                     (3 abas, só o que é exibido)

A versão reduzida é a comunicação intermediária com o patrocinador: aulas síncronas
(perfil de inscrição), workshops (com mapa de calor rotulado) e mentorias. Também poda o JSON embutido, para que
dados que não aparecem na página (qualidade das bases, cruzamentos, itens do formulário
etc.) não fiquem visíveis no código-fonte.

Uso: python3 scripts/gerar_versao_reduzida.py [entrada.html] [saida.html]
"""
import json
import re
import sys

src = sys.argv[1] if len(sys.argv) > 1 else '_completo/formacoes-completo.html'
dst = sys.argv[2] if len(sys.argv) > 2 else 'formacoes.html'
page = open(src, encoding='utf-8').read()


def rx(text):
    """Trecho literal -> regex que tolera diferenças de espaços/quebras de linha."""
    return r'\s+'.join(re.escape(p) for p in text.split())


def cut(start, end, keep_end=True, optional=False):
    """Remove de `start` até (sem incluir) `end`."""
    global page
    m = re.search(rx(start), page)
    if not m:
        if optional:
            return
        raise SystemExit('início não encontrado: ' + start[:70])
    n = re.search(rx(end), page[m.start():])
    if not n:
        raise SystemExit('fim não encontrado: ' + end[:70])
    stop = m.start() + (n.start() if keep_end else n.end())
    page = page[:m.start()] + page[stop:]


def sub(old, new):
    global page
    m = re.search(rx(old), page)
    if not m:
        raise SystemExit('trecho não encontrado: ' + old[:70])
    page = page[:m.start()] + new + page[m.end():]


# ---------------- Abas: remove Trilha do Participante e Relatório Institucional ----------------
sub('<div class="tab" role="tab" data-tab="fx-trilha">Trilha do Participante</div>', '')
sub('<div class="tab" role="tab" data-tab="fx-relatorio">Relatório Institucional</div>', '')
cut('<!-- ======================= ABA 4: TRILHA', '</div> <footer>')

# ---------------- Aulas Síncronas ----------------
sub('Inscrições e participação nas aulas online de SP, PE, DF, BA e RN. Mesmos indicadores do painel de inscrições, '
    'acrescidos de presença, certificação e conhecimento prévio dos participantes.',
    'Inscrições e perfil das pessoas inscritas nas aulas online de SP, PE, DF, BA e RN, com os mesmos indicadores '
    'do painel de inscrições.')
cut('<div class="note-box"> <strong>Leitura com cautela', '<div class="chips" id="fx-chips-aulas">')
cut('<div class="subhead-row"> <h3>Participação, horas e certificação</h3>',
    '<div class="subhead-row"> <h3>Indicadores de perfil</h3>')
cut('<div class="subhead-row"> <h3>Retenção: presença em cada aula</h3>',
    '<div class="subhead-row"><h3>Perfil de quem se inscreveu</h3>')
cut('<div class="subhead-row"> <h3>Conhecimento prévio sobre os temas das aulas</h3>',
    '</div> <!-- ======================= ABA 2')

# ---------------- Workshops ----------------
sub('<table class="datatable" id="t-w-sess"><thead><tr><th>Data</th><th>Localidade</th><th>Facilitação</th>'
    '<th class="num">Formulários</th></tr></thead>',
    '<table class="datatable" id="t-w-sess" data-modo="mentoria"><thead><tr><th>Data</th><th>Localidade</th>'
    '<th class="num">Formulários</th><th class="num">Horas de Mentoria</th></tr></thead>')
sub('de 3 nos itens I a XIII', 'de 3 nos 13 itens avaliados')
sub('Data, localidade, facilitação e formulários recebidos', 'Data, localidade, formulários recebidos e horas de mentoria')
cut('<div class="subhead-row"> <h3>Qualidade percebida por item</h3>',
    '<div class="subhead-row"><h3>Mapa de calor')
sub('<div class="quote melhoria">“Tempo muito curto para a abrangência do conteúdo proposto.”<small>Ponto de melhoria</small></div>',
    '<div class="quote">“O evento é tão maravilho[so] que o tempo passou tão rápido”<small>Participante · avaliação do workshop</small></div>')
sub('<div class="quote melhoria">“A avaliação foi feita às pressas, poderia ser um link no Google Drive.”<small>Ponto de melhoria</small></div>',
    '<div class="quote melhoria">“Poderia haver um link digital para responder à avaliação com mais calma.”<small>Sugestão de participante</small></div>')
sub('Trechos literais dos formulários', 'Trechos dos formulários')
cut('<div class="subhead-row"><h3>Qualidade dos dados desta base</h3></div>',
    '</div> <!-- ======================= ABA 3')

# ---------------- Mentorias ----------------
sub('Participação, horas e certificação das pessoas convocadas para as mentorias online, e o que a pontuação da '
    'inscrição revela sobre quem se manteve no processo.',
    'Participação e certificação das pessoas convocadas para as mentorias online e perfil de quem chegou às mentorias.')
def card_re(titulo):
    """Um card inteiro: termina no </div> que fecha o card (seguido de outro card ou do fim da linha)."""
    return re.compile(r'<div class="card[^"]*">\s*<h3>' + re.escape(titulo) + r'</h3>.*?</div>\s*(?=<div class="card|</div>)', re.S)


for titulo in ('Horas Totais de Mentoria', 'Média por Participante', 'Sem Nenhuma Hora', 'Origem na Base de Inscrições'):
    m = card_re(titulo).search(page)
    if not m:
        raise SystemExit('card não encontrado: ' + titulo)
    page = page[:m.start()] + page[m.end():]
# Multicandidatura sobe para a primeira linha (4 cards) e a segunda linha de cards some
m = card_re('Multicandidatura').search(page)
card = m.group(0)
page = page[:m.start()] + page[m.end():]
row2 = re.search(r'<div class="cards">\s*</div>\s*', page)
if not row2:
    raise SystemExit('segunda linha de cards não ficou vazia')
page = page[:row2.start()] + page[row2.end():]
ini = page.index('id="fx-mentorias"')            # há um card "Certificados" também na aba Workshops
m = card_re('Certificados').search(page, ini)
page = page[:m.end()] + card + page[m.end():]
cut('<div class="subhead-row"><h3>Horas e certificação</h3></div>',
    '<div class="subhead-row"><h3>Perfil de quem chegou às mentorias</h3>')
cut('<div class="subhead-row"><h3>Qualidade dos dados desta base</h3></div>',
    '</div> </div> <footer>')

# ---------------- JSON: mantém só o que a página exibe ----------------
m = re.search(r'(<script id="dados" type="application/json">)(.*?)(</script>)', page, re.S)
D = json.loads(m.group(2))
T = True
SPEC = {
    'meta': T,
    'aulas': {**{k: {'rows': T, 'pessoas_enviadas': T, 'demo': T, 'ind': T, 'linguagens_top': T, 'semanas': T}
                 for k in ('ALL', 'SP', 'PE', 'DF', 'BA', 'RN')},
              'pessoas_em_mais_de_um_territorio': T},
    'workshops': {
        'respostas': T, 'n_localidades': T, 'n_sessoes': T, 'indice_satisfacao': T, 'media_geral': T,
        'pct_nota3': T, 'pct_nota_ate1': T, 'rotulos': T,
        'itens': [{'item': T, 'media': T}],
        'item_xiv': T, 'item_xv': T, 'item_xiv_por_uf': T, 'item_xv_por_uf': T,
        'localidades': [{'loc': T, 'uf': T, 'cidade': T, 'n': T, 'itens': T, 'media': T}],
        'inscricoes': {
            **{k: {'rows': T, 'pessoas_enviadas': T, 'certificados': T, 'certificados_enviadas': T, 'taxa_certificacao': T,
                   'demo': T, 'ind': T, 'linguagens_top': T, 'semanas': T, 'equidade_funil': T}
               for k in ('ALL', 'SP', 'PE', 'DF', 'BA', 'RN')},
            'por_localidade': T, 'status_por_localidade': T},
        'sessoes': [{'loc': T, 'data': T, 'n': T, 'horas_mentoria': T}],
        'pontos_fortes': {'temas': T, 'n_com_conteudo': T, 'sem_tema': T},
        'pontos_fracos': {'temas': T, 'n_textos': T, 'sem_ponto_fraco': T, 'n_com_conteudo': T},
    },
    'mentorias': {
        'total': T, 'titulares': T, 'suplentes': T, 'sem_classificacao': T, 'ativos': T, 'taxa_ativacao': T,
        'cert_sim': T, 'taxa_cert_total': T, 'taxa_cert_ativos': T,
        'perfil_localizados': {'multi_modalidade': T},
    },
    'trilha': {'perfil_etapas': {k: T for k in ('inscricoes_original', 'mentorias_candidatos',
                                                'mentorias_convocados', 'mentorias_ativos')}},
}


def prune(obj, spec):
    if spec is True:
        return obj
    if isinstance(spec, list):
        return [prune(x, spec[0]) for x in obj]
    return {k: prune(obj[k], s) for k, s in spec.items() if k in obj}


payload = json.dumps(prune(D, SPEC), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
page = page[:m.start()] + m.group(1) + payload + m.group(3) + page[m.end():]

# ---------------- Verificações ----------------
for proibido in ('fx-trilha', 'fx-relatorio', 'c-know', 'c-rt-SP', 'c-w-itens', 'c-m-horas', 't-m-opp'):
    assert 'id="%s"' % proibido not in page and 'data-tab="%s"' % proibido not in page, proibido
open(dst, 'w', encoding='utf-8').write(page)
print('ok ->', dst, len(page), 'bytes; JSON', len(payload), 'bytes (completo:', len(m.group(2)), ')')
