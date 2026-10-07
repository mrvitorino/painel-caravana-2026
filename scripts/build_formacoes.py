#!/usr/bin/env python3
"""Calcula os indicadores do painel de execução (aulas síncronas, workshops, mentorias, trilha).

Uso: python3 build_formacoes.py --exec <BaseDeDados_Aulas_Workshops_Mentorias.xlsx> \
        --db data/DB_Inscritos_Caravana2026.xlsx --out <formacoes_data.json> --html formacoes.html

`--html` substitui o bloco <script id="dados" type="application/json"> de formacoes.html
pelos números recalculados (a página inteira é alimentada por esse JSON).

A saída contém apenas agregados (nenhum nome, CPF, e-mail ou telefone).
"""
import argparse, json, re, unicodedata
import numpy as np
import pandas as pd

TERRS = ['SP', 'PE', 'DF', 'BA', 'RN']
CAPITAL = {'SP': 'sao paulo', 'PE': 'recife', 'BA': 'salvador', 'DF': 'brasilia', 'RN': 'natal'}
CERT_MIN_H = 10  # regra observada nos dados (SP/DF): Sim <=> >= 10h de 12h (>= 75%)


def nz(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', s)).strip()


def digits(s):
    return re.sub(r'\D', '', str(s)) if pd.notna(s) else None


def pct(n, d, nd=1):
    return round(100 * n / d, nd) if d else None


def py(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return None if np.isnan(o) else float(o)
    if isinstance(o, dict): return {str(k): py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [py(x) for x in o]
    return o


def vc(series, order=None):
    c = series.value_counts()
    if order:
        return {k: int(c.get(k, 0)) for k in order}
    return {k: int(v) for k, v in c.items()}


# --------------------------------------------------------------------------------------
# AULAS SÍNCRONAS
# --------------------------------------------------------------------------------------
def load_aulas(path):
    frames = []
    for t in TERRS:
        d = pd.read_excel(path, sheet_name=f'Base{t}')
        d.columns = [re.sub(r'\s+', ' ', str(c)).strip() for c in d.columns]
        d['terr'] = t
        ac = [c for c in d.columns if c.upper().startswith('AULA')]
        d['_ac'] = [ac] * len(d)
        for i, c in enumerate(ac, 1):
            d[f'a{i}'] = d[c]
        d['n_aulas_prev'] = len(ac)
        d['aulas_hours'] = [list(map(lambda x: x, [d.loc[i, c] for c in ac])) for i in d.index]
        d['h'] = d[ac].sum(axis=1)
        d['n_aulas'] = d[ac].notna().sum(axis=1)
        d['cpf'] = d['CPF Inscrito'].map(digits)
        d['em'] = d['E-mail'].astype(str).str.lower().str.strip()
        d['nm'] = d['Nome'].map(nz)
        frames.append(d)
    a = pd.concat(frames, ignore_index=True)
    a['status_g'] = a['Status'].map(lambda s: 'enviada' if s == 'enviada' else
                                    'draft' if s == 'draft' else
                                    'aband_socio' if 'sociocultural' in str(s) else 'aband_quest')
    return a, {t: len([c for c in a[a.terr == t]['_ac'].iloc[0]]) for t in TERRS}


def age_at(row):
    try:
        b = pd.to_datetime(row['Data de Nascimento'], dayfirst=True, errors='coerce')
        r = pd.to_datetime(row['Data de Inscrição'], dayfirst=True, errors='coerce')
        if pd.isna(b) or pd.isna(r): return np.nan
        age = (r - b).days / 365.25
        return age if 14 <= age <= 90 else np.nan
    except Exception:
        return np.nan


def band(age):
    if pd.isna(age): return 'Sem dado'
    for lo, hi, lab in [(0, 20, 'Até 19'), (20, 25, '20 a 24'), (25, 30, '25 a 29'), (30, 35, '30 a 34'), (35, 40, '35 a 39'),
                        (40, 45, '40 a 44'), (45, 50, '45 a 49'), (50, 55, '50 a 54'), (55, 60, '55 a 59'), (60, 200, '60 ou mais')]:
        if lo <= age < hi: return lab
    return 'Sem dado'


BANDS = ['Até 19', '20 a 24', '25 a 29', '30 a 34', '35 a 39', '40 a 44', '45 a 49', '50 a 54', '55 a 59', '60 ou mais', 'Sem dado']
GEN_ORDER = ['Mulher Cis', 'Homem Cis', 'Pessoa não binária', 'Mulher Trans', 'Homem Trans', 'Prefiro não responder', 'Sem resposta']
RACE_ORDER = ['Branca', 'Parda', 'Preta', 'Amarela', 'Indígena', 'Prefiro não responder', 'Sem resposta']
FORM_MAP = {'Pós-graduação': 'Pós-graduação', 'Ensino Superior (completo)': 'Superior completo',
            'Ensino Superior (incompleto)': 'Superior incompleto', 'Ensino Médio (completo)': 'Médio completo',
            'Ensino Médio (incompleto)': 'Médio incompleto',
            'Ensino Fundamental II (completo)': 'Fundamental', 'Ensino Fundamental II (incompleto)': 'Fundamental',
            'Ensino Fundamental I (completo)': 'Fundamental', 'Ensino Fundamental I (incompleto)': 'Fundamental'}
FORM_ORDER = ['Pós-graduação', 'Superior completo', 'Superior incompleto', 'Médio completo', 'Médio incompleto', 'Fundamental', 'Outros', 'Sem resposta']
KNOW_TOPICS = {
    'captacao': 'Captação de Recursos', 'gestao': 'Gestão e Prestação de Contas',
    'ia': 'Inteligência Artificial na cultura', 'rouanet': 'Fomento Indireto (Lei Rouanet)'}
KNOW_KEYS = {'Captação de Recursos': 'captacao', 'Gestão e Prestação de Contas': 'gestao',
             'Inteligência Artificial': 'ia', 'Fomento Indireto': 'rouanet'}

NEG = re.compile(r'^(nao|n|nao tenho|nao possuo|nenhum|nenhuma|nego|nao se aplica|nao obrigad[oa]|nao necessito|nao precisa|nao e necessario|nao tenho necessidade)\b')


def classify_access(txt):
    if pd.isna(txt): return 'Sem resposta'
    t = nz(txt)
    if t in ('sem resposta', ''): return 'Sem resposta'
    if NEG.match(t) and not re.search(r'(autis|tdah|dislex|surdez|visao|auditiv|labial|neurodiv|escada|fibromialg|transporte)', t):
        return 'Sem necessidade'
    return 'Necessidade declarada'


def access_theme(txt):
    t = nz(txt)
    themes = []
    if re.search(r'(visao|visual|fonte|letras|texto)', t): themes.append('Visual / leitura')
    if re.search(r'(surdez|auditiv|labial|repetir)', t): themes.append('Auditiva')
    if re.search(r'(autis|tdah|dislex|neurodiv|barulho|atencao|camera|previsibilidade|interpretar)', t): themes.append('Neurodivergência / sensorial')
    if re.search(r'(escada|cadeira|fibromialg|transporte)', t): themes.append('Mobilidade / conforto')
    if not themes: themes.append('Outras')
    return themes


def person_table(a):
    """Uma linha por pessoa (CPF), priorizando envio e maior carga de presença."""
    a = a.copy()
    a['pr'] = a['status_g'].map({'enviada': 0, 'draft': 1, 'aband_quest': 2, 'aband_socio': 3})
    a = a.sort_values(['cpf', 'pr', 'h'], ascending=[True, True, False])
    return a.drop_duplicates('cpf', keep='first')


def perfil_demografico(env_people, key):
    """Perfil de pessoas únicas com inscrição enviada (gênero, raça, formação, idade, PcD, povos, indicadores...).
    `env_people` precisa de: terr, Gênero, Cor/Raça, Formação, UF Inscrito, Cidade inscrito, Data de Inscrição etc."""
    # demografia (pessoas únicas com inscrição enviada)
    out = {}
    e = env_people.copy()
    e['idade_calc'] = e.apply(age_at, axis=1)
    e['faixa'] = e['idade_calc'].map(band)
    e['gen'] = e['Gênero'].fillna('Sem resposta')
    e['raca'] = e['Cor/Raça'].fillna('Sem resposta')
    e['form'] = e['Formação'].map(lambda x: 'Sem resposta' if pd.isna(x) else FORM_MAP.get(x, 'Outros'))
    n = len(e)
    resp_g = e[e.gen != 'Sem resposta']; resp_r = e[e.raca != 'Sem resposta']; resp_f = e[e.form != 'Sem resposta']
    out['demo'] = {
        'genero': vc(e.gen, GEN_ORDER), 'raca': vc(e.raca, RACE_ORDER), 'formacao': vc(e.form, FORM_ORDER), 'idade': vc(e.faixa, BANDS),
        'idade_mediana': round(float(e['idade_calc'].median()), 1) if e['idade_calc'].notna().any() else None,
    }
    pcd = e['Pessoa com deficiência?'].fillna('Sem resposta')
    out['demo']['pcd'] = {'Não sou': int((pcd == 'Não sou').sum()), 'Deficiência declarada': int(pcd.str.startswith('Sim').sum()),
                          'Sem resposta': int((pcd == 'Sem resposta').sum())}
    out['demo']['pcd_tipos'] = {k.replace('Sim, Deficiência ', ''): int(v) for k, v in pcd[pcd.str.startswith('Sim')].value_counts().items()}
    povos = e['Comunidades Tradicionais/Povos'].fillna('Sem resposta')
    pc = {'Povos de Terreiro': 0, 'Sertanejos/Catingueiros': 0, 'Quilombolas': 0, 'Ribeirinhos': 0, 'Outros povos e comunidades': 0}
    n_trad = 0
    for v in povos:
        if v in ('Não', 'Não sei', 'Sem resposta'): continue
        parts = [p.strip() for p in v.split(',') if p.strip() not in ('Não', 'Não sei', '')]
        if not parts: continue
        n_trad += 1
        for p in parts:
            if p == 'Povos de Terreiro': pc['Povos de Terreiro'] += 1
            elif p in ('Sertanejos', 'Catingueiros'): pc['Sertanejos/Catingueiros'] += 1
            elif p == 'Quilombolas': pc['Quilombolas'] += 1
            elif p == 'Ribeirinhos': pc['Ribeirinhos'] += 1
            elif p in ('Não sei',): pass
            else: pc['Outros povos e comunidades'] += 1
    out['demo']['povos'] = {'Não': int((povos == 'Não').sum()), 'Não sei': int((povos == 'Não sei').sum()),
                            'Sem resposta': int((povos == 'Sem resposta').sum()), **pc}
    out['demo']['pessoas_povos_tradicionais'] = n_trad
    # indicadores
    out['ind'] = {
        'equidade_genero': {'n': int(resp_g.gen.isin(['Mulher Cis', 'Mulher Trans', 'Pessoa não binária']).sum()), 'd': len(resp_g)},
        'repr_racial': {'n': int(resp_r.raca.isin(['Preta', 'Parda', 'Indígena']).sum()), 'd': len(resp_r)},
        'qualificacao': {'n': int(resp_f.form.isin(['Pós-graduação', 'Superior completo']).sum()), 'd': len(resp_f)},
    }
    inside = e['UF Inscrito'].str.upper().str.strip() == (key if key != 'ALL' else e['terr'])
    out['ind']['mesmo_estado'] = {'n': int(inside.sum()), 'd': n}
    caps = e.apply(lambda r: nz(r['Cidade inscrito']) == CAPITAL[r['terr']], axis=1)
    if key == 'DF':
        out['ind']['interior'] = None
    elif key == 'ALL':
        nd = e[e.terr != 'DF']; cd = caps[nd.index]
        out['ind']['interior'] = {'n': int((~cd).sum()), 'd': len(nd)}
    else:
        out['ind']['interior'] = {'n': int((~caps).sum()), 'd': n}
    # conhecimento prévio
    kc = [c for c in e.columns if c.startswith('Sobre ')]
    know = {}
    for c in kc:
        k = next(v for kk, v in KNOW_KEYS.items() if kk in c)
        lv = e[c].map(lambda s: int(re.match(r'Nível (\d)', s).group(1)) if isinstance(s, str) and s.startswith('Nível') else np.nan)
        v = lv.dropna()
        know[k] = {'n': len(v), 'dist': {str(i): int((v == i).sum()) for i in range(1, 5)},
                   'media': round(float(v.mean()), 2) if len(v) else None, 'pct_baixo': pct(int((v <= 2).sum()), len(v))}
    out['conhecimento'] = know
    # acessibilidade
    ac_col = [c for c in e.columns if c.startswith('Você possui')][0]
    cl = e[ac_col].map(classify_access)
    out['acessibilidade'] = {k: int((cl == k).sum()) for k in ['Sem necessidade', 'Necessidade declarada', 'Sem resposta']}
    th = {}
    for t in e[cl == 'Necessidade declarada'][ac_col]:
        for x in access_theme(t): th[x] = th.get(x, 0) + 1
    out['acessibilidade_temas'] = th
    # linguagens de interesse
    lg = {}
    for v in e['Linguagens de Interesse'].dropna():
        for p in v.split(','):
            p = p.strip()
            if p: lg[p.title() if p.lower() == p else p] = lg.get(p.title() if p.lower() == p else p, 0) + 1
    # normaliza chave
    lg2 = {}
    for k, v in lg.items(): lg2[nz(k)] = lg2.get(nz(k), 0) + v
    names = {nz(k): ('Museografia / acervos' if nz(k).startswith('exposicoes de artes visuais') else k.strip().title()) for k in lg}
    top = sorted(lg2.items(), key=lambda kv: -kv[1])[:10]
    out['linguagens_top'] = [[names[k], v] for k, v in top]
    # inscrições por semana (pessoas únicas, 1ª inscrição enviada)
    dts = pd.to_datetime(e['Data de Inscrição'], dayfirst=True, errors='coerce')
    wk = (dts - pd.to_timedelta(dts.dt.weekday, unit='D')).dt.strftime('%Y-%m-%d').value_counts().sort_index()
    out['semanas'] = [[k, int(v)] for k, v in wk.items()]
    return out, e


def aulas_block(a, planned, key):
    sub = a if key == 'ALL' else a[a.terr == key]
    out = {}
    out['rows'] = {'total': len(sub), 'enviada': int((sub.status_g == 'enviada').sum()), 'draft': int((sub.status_g == 'draft').sum()),
                   'aband_socio': int((sub.status_g == 'aband_socio').sum()), 'aband_quest': int((sub.status_g == 'aband_quest').sum())}
    pt = person_table(sub)
    env_people = person_table(sub[sub.status_g == 'enviada'])
    out['pessoas_total'] = len(pt)
    out['pessoas_enviadas'] = len(env_people)
    part = env_people[env_people.n_aulas > 0]
    out['participantes'] = len(part)
    # a taxa considera só territórios com presença registrada (a BaseRN traz apenas inscrições)
    com_presenca = sub[sub.terr.map(lambda t: planned.get(t, 0) > 0)]
    base_taxa = person_table(com_presenca[com_presenca.status_g == 'enviada'])
    out['taxa_participacao'] = pct(len(part), len(base_taxa))
    out['horas_aluno'] = float(sub['h'].sum()) if key == 'ALL' else float(sub['h'].sum())
    out['horas_media_participante'] = round(float(part['h'].mean()), 1) if len(part) else None
    # frequência: nº de aulas assistidas entre participantes
    if key != 'ALL':
        n_pl = planned[key]
        out['aulas_previstas_na_base'] = n_pl
        out['freq'] = {str(i): int((part.n_aulas == i).sum()) for i in range(1, n_pl + 1)}
        cols = [f'a{i}' for i in range(1, n_pl + 1)]
        out['presenca_por_aula'] = [int(sub[c].notna().sum()) for c in cols]
        out['horas_por_aula'] = [float(sub[c].dropna().iloc[0]) if sub[c].notna().any() else None for c in cols]
        out['carga_prevista_h'] = float(sum(v for v in out['horas_por_aula'] if v) ) if all(v for v in out['horas_por_aula'][:1]) else None
        out['aulas_com_registro'] = int(sum(1 for c in cols if sub[c].notna().any()))
        cert_avail = sub['CERTIFICADO'].notna().any() if 'CERTIFICADO' in sub.columns else False
        out['cert_disponivel'] = bool(cert_avail)
        if cert_avail:
            cp = env_people[env_people.n_aulas > 0]
            cs = person_table(sub[sub['CERTIFICADO'] == 'Sim'])
            out['cert_sim'] = len(cs)
            out['cert_pct_participantes'] = pct(len(cs), len(part))
            out['cert_ge_min'] = int((part.h >= CERT_MIN_H).sum())
        else:
            out['cert_sim'] = None
    pdm, e = perfil_demografico(env_people, key)
    out.update(pdm)
    return out, e


def equity_funnel(a):
    """Participação de grupos prioritários em cada etapa (pessoas únicas)."""
    env = person_table(a[a.status_g == 'enviada']).copy()
    env['mulher'] = env['Gênero'].isin(['Mulher Cis', 'Mulher Trans', 'Pessoa não binária'])
    env['pp'] = env['Cor/Raça'].isin(['Preta', 'Parda', 'Indígena'])
    env['rg'] = env['Gênero'].notna(); env['rr'] = env['Cor/Raça'].notna()
    part = env[env.n_aulas > 0]
    cert = env[(env.terr.isin(['SP', 'DF'])) & (env['CERTIFICADO'] == 'Sim')]
    base_cert = part[part.terr.isin(['SP', 'DF'])]
    def share(d, col, resp):
        dd = d[d[resp]]
        return {'n': int(dd[col].sum()), 'd': len(dd), 'pct': pct(int(dd[col].sum()), len(dd))}
    env_spdf = env[env.terr.isin(['SP', 'DF'])]
    return {
        'inscritos_sp_df': {'mulher': share(env_spdf, 'mulher', 'rg'), 'pp': share(env_spdf, 'pp', 'rr')},
        'inscritos': {'mulher': share(env, 'mulher', 'rg'), 'pp': share(env, 'pp', 'rr')},
        'participantes': {'mulher': share(part, 'mulher', 'rg'), 'pp': share(part, 'pp', 'rr')},
        'participantes_sp_df': {'mulher': share(base_cert, 'mulher', 'rg'), 'pp': share(base_cert, 'pp', 'rr')},
        'certificados_sp_df': {'mulher': share(cert, 'mulher', 'rg'), 'pp': share(cert, 'pp', 'rr')},
    }


# --------------------------------------------------------------------------------------
# WORKSHOPS
# --------------------------------------------------------------------------------------
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII']

STRENGTH_THEMES = {
    'Conteúdo e aprendizado': r'(conteudo|aprend|conhecimento|informac|aprofund|clareza|elaborac|projeto|captac|5ps)',
    'Didática e facilitação': r'(didatic|facilita|palestr|explic|professor|condu|mediac|metodolog|domin|equipe tecnica|ministr|oficineir)',
    'Prática e dinâmica': r'(pratic|dinamic|mao na massa|oficina|exercicio|atividade|vivencia|confecc|jogo)',
    'Troca e interação': r'(interac|troca|networking|conexao|encontro|rede|colet|roda|participac|conversa|saberes|compartilh|pessoas)',
    'Esclarecimento e clareza': r'(esclarec|duvida|clara|clareza|objetiv|linguagem acessivel|simples)',
    'Diversidade e conexão territorial': r'(diversidade|territ|atores|cidade|fomento|articulac|integrac|partilha|incentivo|incetivo|networking|netnarking)',
    'Organização e acolhimento': r'(organizac|estrutura|acolh|lanche|espaco|local|equipe|staff|recepc|cuidado|atencao|pontual|logistic)',
}
WEAK_NONE = r'^(nao|nenhum|nenhuma|nada|n a|sem|nao houve|nao teve|nao ha|nao tem|nao percebi|nao vi|nao observei|nao encontrei|tudo|zero|x|ñ|-)\b'
WEAK_THEMES = {
    'Pouco tempo / carga horária': r'(tempo|curto|curta|duracao|mais horas|horas|corrido|rapido|apertado|poucos dias|dois dias|mais dia|um dia|mais encontros|continuidade|mais aulas|carga hor|breve|acabou|1 mes|mais 1)',
    'Poucos participantes / divulgação': r'(divulg|publico|mobiliz|esvaziado|poucas pessoas|poucos participantes|pouca gente|mais gente|mais participante|mais pessoas|quantidade de pessoas|ausencia de mais|falta de interesse|poucas pessoas|nao havia tanta gente|convite|grupos culturais)',
    'Horário e pontualidade': r'(atraso|passou do horario|horario|pontual|sabado|a noite|cumprimento do planejamento)',
    'Estrutura e conforto': r'(frio|calor|ar condicionado|som|microfone|cadeira|barulho|lanche|coffee|cafe|almoco|alimentac|banheiro|internet|espaco|local|sala|estacionamento|acustica|projetor|climatizac|kit|caneta|caderno|logistica)',
    'Metodologia e aprofundamento': r'(aprofund|captacao|mais conteudo|exemplo|material|apostila|slides|mais pratic|teoria|tecnico|detalh|prestacao|muita fala|dinamiz|quantidade de temas|conteudo e extenso)',
    'Aplicação da avaliação': r'(avaliacao|feedback|formulario|link|pressas)',
    'Acessibilidade': r'(acessibilidade|neurodiv)',
}


def yn(v):
    if pd.isna(v): return None
    t = nz(v)
    if t in ('sim', 's'): return 'Sim'
    if t in ('nao', 'n', 'nao '): return 'Não'
    return None


ROTULOS_WORKSHOP = {
    'I': ('Fortalece a atuação no território', 'Os conteúdos abordados servirão para fortalecer sua atuação junto ao coletivo/território?'),
    'II': ('Metodologia das facilitadoras', 'A metodologia utilizada pelas facilitadoras colaborou para o entendimento dos conteúdos e práticas?'),
    'III': ('Domínio do conteúdo', 'As facilitadoras demonstraram conhecimento do conteúdo abordado?'),
    'IV': ('Motivação e envolvimento', 'As facilitadoras conseguiram motivar e envolver os participantes?'),
    'V': ('Expectativas atendidas', 'Em termos gerais, o encontro alcançou suas expectativas em relação aos conteúdos propostos?'),
    'VI': ('Aplicabilidade na prática', 'O conteúdo abordado se mostrou aplicável na prática?'),
    'VII': ('Divulgação eficiente', 'A divulgação foi eficiente no território?'),
    'VIII': ('Divulgação clara', 'A divulgação dos conteúdos e práticas foi clara e condizente com o desenvolvimento?'),
    'IX': ('Informações de inscrição e seleção', 'As informações sobre inscrição e seleção foram transmitidas de forma clara e eficiente?'),
    'X': ('Tempo de duração do encontro', 'O tempo de duração do encontro possibilitou o desenvolvimento do tema?'),
    'XI': ('Espaço e acessibilidade estrutural', 'O espaço de realização foi acolhedor e contou com acessibilidade estrutural?'),
    'XII': ('Acessibilidade de conteúdo', 'Os encontros, desde a divulgação, contaram com acessibilidade de conteúdo?'),
    'XIII': ('Recursos e organização', 'O encontro teve recursos (equipamentos, materiais, organização etc.) coerentes com a sua proposta inicial?'),
    'XIV': ('Objetivos específicos = metas (resposta correta: Sim)', 'Verdadeiro ou falso: os objetivos específicos de um projeto correspondem às suas metas (mensuráveis e quantificáveis). Resposta correta: SIM.'),
    'XV': ('Divisão fixa do orçamento (resposta correta: Não)', 'Verdadeiro ou falso: todas as leis de incentivo dividem os orçamentos em 50% custos administrativos, 10% captação e 40% produção. Resposta correta: NÃO.'),
}


def _aba_avaliacao(path):
    nomes = pd.ExcelFile(path).sheet_names
    return 'BaseAvaliacaoWorkshops' if 'BaseAvaliacaoWorkshops' in nomes else 'BaseWorkshops'


def workshops_block(path):
    w = pd.read_excel(path, sheet_name=_aba_avaliacao(path))
    cols = list(w.columns)
    item_cols = cols[5:18]
    yn14, yn15 = cols[18], cols[19]
    txt_s, txt_w, txt_c, txt_x = cols[20], cols[21], cols[22], cols[23]
    w = w.rename(columns={c: r for c, r in zip(item_cols, ROMAN)})
    for r in ROMAN:
        w[r] = pd.to_numeric(w[r], errors='coerce')
        w.loc[~w[r].isin([0, 1, 2, 3]), r] = np.nan
    all5 = pd.read_excel(path, sheet_name=_aba_avaliacao(path))[cols[5:18]].apply(pd.to_numeric, errors='coerce').eq(5).sum(axis=1) >= 1
    pass  # valores fora de 0-3 (ex.: 5) já foram descartados acima
    n_resp = len(w)
    out = {'respostas': n_resp, 'respostas_escala_invalida': int(all5.sum())}
    w['loc'] = w['Localidade']; w['uf'] = w['Localidade'].str[:2]
    out['n_localidades'] = int(w['loc'].nunique()); out['n_sessoes'] = int(w.groupby(['loc', 'Data']).ngroups)
    out['datas'] = [str(w['Data'].min().date()), str(w['Data'].max().date())]
    sc = w[ROMAN]
    vals = sc.stack()
    out['n_notas'] = int(len(vals))
    out['media_geral'] = round(float(vals.mean()), 2)
    out['indice_satisfacao'] = round(float(vals.mean()) / 3 * 100, 1)
    out['pct_nota3'] = pct(int((vals == 3).sum()), len(vals))
    out['pct_nota_ate1'] = pct(int((vals <= 1).sum()), len(vals))
    out['pct_nota_ate2_ou_mais'] = pct(int((vals >= 2).sum()), len(vals))
    items = []
    for r in ROMAN:
        v = w[r].dropna()
        items.append({'item': r, 'n': len(v), 'media': round(float(v.mean()), 2), 'pct3': pct(int((v == 3).sum()), len(v)),
                      'pct_ate1': pct(int((v <= 1).sum()), len(v))})
    out['itens'] = items
    w['idx'] = w[ROMAN].mean(axis=1)
    locs = []
    for l, g in w.groupby('loc'):
        fac = g['Facilitador'].dropna().unique().tolist()
        locs.append({'loc': l, 'uf': l[:2], 'cidade': l.split('/')[1], 'n': len(g), 'datas': sorted({str(d.date()) for d in g['Data']}),
                     'facilitador': fac[0] if fac else None, 'media': round(float(g[ROMAN].stack().mean()), 2),
                     'indice': round(float(g[ROMAN].stack().mean()) / 3 * 100, 1),
                     'pct3': pct(int((g[ROMAN].stack() == 3).sum()), int(g[ROMAN].stack().count())),
                     'itens': [round(float(g[r].mean()), 2) if g[r].notna().any() else None for r in ROMAN]})
    order = {'SP': 0, 'PE': 1, 'DF': 2, 'BA': 3, 'RN': 4}
    locs.sort(key=lambda x: (order[x['uf']], x['cidade']))
    out['localidades'] = locs
    ufs = []
    for u, g in w.groupby('uf'):
        ufs.append({'uf': u, 'n': len(g), 'localidades': int(g['loc'].nunique()),
                    'indice': round(float(g[ROMAN].stack().mean()) / 3 * 100, 1), 'media': round(float(g[ROMAN].stack().mean()), 2)})
    ufs.sort(key=lambda x: order[x['uf']])
    out['ufs'] = ufs
    sess = []
    for (l, d), g in w.groupby(['loc', 'Data']):
        sess.append({'loc': l, 'data': str(d.date()), 'n': len(g), 'facilitador': (g['Facilitador'].dropna().iloc[0] if g['Facilitador'].notna().any() else None)})
    sess.sort(key=lambda x: x['data'])
    # Horas de mentoria: 6h por localidade, divididas pelos dias de workshop
    # (1 dia = 6h; 2 dias = 3h por dia; 3 dias = 2h por dia).
    dias = {}
    for x in sess:
        dias[x['loc']] = dias.get(x['loc'], 0) + 1
    for x in sess:
        x['horas_mentoria'] = round(6 / dias[x['loc']], 1) if dias[x['loc']] else None
        if x['horas_mentoria'] is not None and x['horas_mentoria'] == int(x['horas_mentoria']):
            x['horas_mentoria'] = int(x['horas_mentoria'])
    out['sessoes'] = sess
    out['rotulos'] = {k: {'curto': v[0], 'completo': v[1]} for k, v in ROTULOS_WORKSHOP.items()}
    out['facilitador_ausente'] = int(w['Facilitador'].isna().sum())
    y14 = w[yn14].map(yn); y15 = w[yn15].map(yn)
    out['item_xiv'] = {'Sim': int((y14 == 'Sim').sum()), 'Não': int((y14 == 'Não').sum()), 'Sem resposta': int(y14.isna().sum())}
    out['item_xv'] = {'Sim': int((y15 == 'Sim').sum()), 'Não': int((y15 == 'Não').sum()), 'Sem resposta': int(y15.isna().sum())}
    out['item_xiv_por_uf'] = {u: pct(int((y14[w.uf == u] == 'Sim').sum()), int(y14[w.uf == u].notna().sum())) for u in order if (w.uf == u).any()}
    out['item_xv_por_uf'] = {u: pct(int((y15[w.uf == u] == 'Sim').sum()), int(y15[w.uf == u].notna().sum())) for u in order if (w.uf == u).any()}
    # duplicatas exatas
    dup = w.duplicated(subset=['loc', 'Data'] + ROMAN + [txt_s, txt_w, txt_c], keep='first')
    out['linhas_duplicadas_exatas'] = int(dup.sum())
    # texto
    def themes(series, themes_map, none_re=None):
        s = series.dropna().astype(str).map(nz)
        s = s[s != '']
        res = {'n_textos': int(len(s))}
        if none_re:
            none_mask = s.map(lambda t: bool(re.match(none_re, t)) and len(t) < 45 and not any(re.search(p, t) for p in themes_map.values()))
            res['sem_ponto_fraco'] = int(none_mask.sum())
            s2 = s[~none_mask]
        else:
            s2 = s
        res['n_com_conteudo'] = int(len(s2))
        res['temas'] = {k: int(s2.map(lambda t: bool(re.search(p, t))).sum()) for k, p in themes_map.items()}
        res['sem_tema'] = int(s2.map(lambda t: not any(re.search(p, t) for p in themes_map.values())).sum())
        return res
    out['pontos_fortes'] = themes(w[txt_s], STRENGTH_THEMES)
    out['pontos_fracos'] = themes(w[txt_w], WEAK_THEMES, WEAK_NONE)
    out['comentarios'] = {'n': int(w[txt_c].notna().sum())}
    # amostra de citações (revisão manual posterior)
    out['_amostra_fortes'] = w[txt_s].dropna().astype(str).str.strip().tolist()
    out['_amostra_fracos'] = w[txt_w].dropna().astype(str).str.strip().tolist()
    out['_amostra_coment'] = w[txt_c].dropna().astype(str).str.strip().tolist()
    return out, w


# --------------------------------------------------------------------------------------
# MENTORIAS + TRILHA
# --------------------------------------------------------------------------------------
def mentorias_block(path, db, resumo_ment):
    m = pd.read_excel(path, sheet_name='BaseMentorias')
    m['em'] = m['E-mail'].astype(str).str.lower().str.strip().replace({'nan': None})
    m['nm'] = m['Nome'].map(nz)
    m['Opp'] = m['Oportunidade'].fillna('Sem classificação').replace({'Mentoria': 'Titular', 'Mentoria - Suplente': 'Suplente'})
    m['h'] = m['Horas'].fillna(0.0)
    m['cert'] = m['Certificado'].eq('Sim')
    m['ativo'] = m['h'] > 0
    # cruzamento com a base de inscrições
    db_by_em = {}
    db_by_nm = {}
    for i, r in db.iterrows():
        if r['em'] and r['em'] != 'nan': db_by_em.setdefault(r['em'], []).append(i)
        db_by_nm.setdefault(r['nm'], []).append(i)
    match_idx = []
    for _, r in m.iterrows():
        idx = db_by_em.get(r['em'], []) or db_by_nm.get(r['nm'], [])
        match_idx.append(idx)
    m['db_idx'] = match_idx
    m['in_db'] = m['db_idx'].map(len).gt(0)
    m['db_cpf'] = m['db_idx'].map(lambda ix: db.loc[ix[0], 'cpf'] if ix else None)
    return m


# --------------------------------------------------------------------------------------
# INSCRIÇÕES E CERTIFICADOS DOS WORKSHOPS (aba BaseInscricaoWorkshops)
# --------------------------------------------------------------------------------------
UFS_VALIDAS = {'SP', 'PE', 'DF', 'BA', 'RN', 'GO', 'PB', 'RR', 'MG', 'RJ', 'CE', 'AL', 'SE', 'MA', 'PI', 'ES', 'PR', 'SC', 'RS', 'MT', 'MS',
               'TO', 'PA', 'AP', 'AM', 'AC', 'RO'}
CATEGORICAS_WS = ['Gênero', 'Cor/Raça', 'Formação', 'Pessoa com deficiência?', 'Comunidades Tradicionais/Povos',
                  'Linguagens de Interesse', 'UF Inscrito']


def load_inscricoes_workshops(path):
    w = pd.read_excel(path, sheet_name='BaseInscricaoWorkshops')
    w.columns = [re.sub(r'\s+', ' ', str(c)).strip() for c in w.columns]
    # a planilha traz números soltos (30 e 35) em campos de texto de linhas incompletas: tratados como "sem resposta"
    for c in CATEGORICAS_WS:
        w[c] = w[c].map(lambda v: np.nan if (pd.isna(v) or re.fullmatch(r'\d+(\.0)?', str(v).strip())) else str(v).strip())
    w['UF Inscrito'] = w['UF Inscrito'].map(lambda v: v.upper() if isinstance(v, str) and v.upper() in UFS_VALIDAS else np.nan)
    w['terr'] = w['Localidade'].str[:2]
    cpf = w['CPF Inscrito'].map(digits)
    w['cpf'] = [c if isinstance(c, str) and c else 'sem-cpf:' + nz(n) for c, n in zip(cpf, w['Nome'])]
    w['status_g'] = w['Status'].map(lambda s: 'enviada' if s == 'enviada' else 'draft' if s == 'draft' else
                                    'aband_socio' if 'sociocultural' in str(s) else 'aband_quest')
    w['cert'] = (w['Certificado'] == 'Sim')
    w['h'] = w['cert'].astype(int)           # desempate em person_table: prefere o registro com certificado
    return w


def inscricoes_ws_block(w, key):
    sub = w if key == 'ALL' else w[w.terr == key]
    sub = sub.copy()
    sub['cert_p'] = sub.groupby('cpf')['cert'].transform('any')   # certificado vale para a pessoa
    out = {'rows': {'total': len(sub), 'enviada': int((sub.status_g == 'enviada').sum()), 'draft': int((sub.status_g == 'draft').sum()),
                    'aband_socio': int((sub.status_g == 'aband_socio').sum()), 'aband_quest': int((sub.status_g == 'aband_quest').sum())}}
    env_people = person_table(sub[sub.status_g == 'enviada'])
    out['pessoas_total'] = int(sub.cpf.nunique())
    out['pessoas_enviadas'] = len(env_people)
    out['certificados'] = int(sub[sub.cert].cpf.nunique())                 # pessoas certificadas (qualquer status de inscrição)
    out['certificados_enviadas'] = int(env_people.cert_p.sum())            # ... entre as pessoas com inscrição enviada
    out['taxa_certificacao'] = pct(out['certificados_enviadas'], out['pessoas_enviadas'])
    pdm, e = perfil_demografico(env_people, key)
    out.update(pdm)
    # equidade ao longo do funil: inscritas/os -> certificadas/os (denominador: quem respondeu à pergunta)
    def share(d, col, resp):
        g = d[d[col].notna()]
        return {'n': int(g[col].isin(resp).sum()), 'd': len(g), 'pct': pct(int(g[col].isin(resp).sum()), len(g))}
    mulher = ['Mulher Cis', 'Mulher Trans', 'Pessoa não binária']; pp = ['Preta', 'Parda', 'Indígena']
    cert = env_people[env_people.cert_p]
    out['equidade_funil'] = {
        'inscritos': {'mulher': share(env_people, 'Gênero', mulher), 'pp': share(env_people, 'Cor/Raça', pp)},
        'certificados': {'mulher': share(cert, 'Gênero', mulher), 'pp': share(cert, 'Cor/Raça', pp)}}
    return out


def inscricoes_workshops(path, wk):
    w = load_inscricoes_workshops(path)
    res = {k: inscricoes_ws_block(w, k) for k in ['ALL', 'SP', 'PE', 'DF', 'BA', 'RN']}
    # por localidade (+ avaliações recebidas e datas, da aba de avaliação)
    aval = {l['loc']: l for l in wk['localidades']}
    horas = {}
    for x in wk['sessoes']:
        horas[x['loc']] = horas.get(x['loc'], 0) + (x['horas_mentoria'] or 0)
    locs = []
    order = {'SP': 0, 'PE': 1, 'DF': 2, 'BA': 3, 'RN': 4}
    for l, g in w.groupby('Localidade'):
        b = inscricoes_ws_block(g, 'ALL')
        locs.append({'loc': l, 'uf': l[:2], 'cidade': l.split('/')[1], 'datas': aval.get(l, {}).get('datas', []),
                     'rows_total': b['rows']['total'], 'enviadas': b['rows']['enviada'], 'pessoas_enviadas': b['pessoas_enviadas'],
                     'certificados': b['certificados'], 'certificados_enviadas': b['certificados_enviadas'], 'taxa_certificacao': b['taxa_certificacao'],
                     'avaliacoes': aval.get(l, {}).get('n', 0), 'horas_mentoria': horas.get(l)})
    locs.sort(key=lambda x: (order[x['uf']], x['cidade']))
    res['por_localidade'] = locs
    raw = pd.read_excel(path, sheet_name='BaseInscricaoWorkshops')
    res['qualidade'] = {
        'linhas': len(raw),
        'linhas_perfil_numerico': int(raw['Gênero'].map(lambda v: bool(re.fullmatch(r'\d+(\.0)?', str(v).strip()))).sum()),
        'registros_cpf_repetido': int(len(w) - w.cpf.nunique()),
        'sem_resposta_genero': res['ALL']['demo']['genero'].get('Sem resposta'),
    }
    res['status_por_localidade'] = [{'loc': x['loc'], **{k: int((w[w.Localidade == x['loc']].status_g == k).sum()) for k in ['enviada', 'draft', 'aband_socio', 'aband_quest']}} for x in locs]
    return res



def build(args):
    a, planned = load_aulas(args.exec)
    db = pd.read_excel(args.db, sheet_name='DB_Inscritos')
    db['cpf'] = db['CPF Inscrito'].map(digits)
    db['em'] = db['E-mail'].astype(str).str.lower().str.strip()
    db['nm'] = db['Nome'].map(nz)
    resumo = pd.read_excel(args.db, sheet_name='DB_ResumoMentorias')
    resumo['nm'] = resumo['Nome'].map(nz)

    res = {'meta': {'fonte': 'BaseDeDados_Aulas_Workshops_Mentorias.xlsx', 'cert_min_h': CERT_MIN_H}}

    # ---------------- AULAS ----------------
    res['aulas'] = {}
    all_e = None
    for key in ['ALL'] + TERRS:
        blk, e = aulas_block(a, planned, key)
        res['aulas'][key] = blk
        if key == 'ALL': all_e = e
    res['aulas']['equidade_funil'] = equity_funnel(a)
    # pessoas em mais de um território
    g = a[a.status_g == 'enviada'].groupby('cpf')['terr'].nunique()
    res['aulas']['pessoas_em_mais_de_um_territorio'] = int((g > 1).sum())
    res['aulas']['cpfs_duplicados_no_mesmo_territorio'] = int(a.groupby(['terr', 'cpf']).size().gt(1).sum())
    res['aulas']['idade_campo_invalido'] = int((pd.to_numeric(a['Idade'], errors='coerce') > 120).sum())
    res['aulas']['registros_PE_BA_horas_total_vazio'] = int(a[a.terr.isin(['PE', 'BA'])]['TOTAL'].isna().sum()) if 'TOTAL' in a.columns else None

    # ---------------- WORKSHOPS ----------------
    wk, wdf = workshops_block(args.exec)
    res['workshops'] = wk
    res['workshops']['inscricoes'] = inscricoes_workshops(args.exec, wk)

    # ---------------- MENTORIAS ----------------
    m = mentorias_block(args.exec, db, resumo)
    mm = {'total': len(m), 'titulares': int((m.Opp == 'Titular').sum()), 'suplentes': int((m.Opp == 'Suplente').sum()),
          'sem_classificacao': int((m.Opp == 'Sem classificação').sum()),
          'ativos': int(m.ativo.sum()), 'zero_h': int((~m.ativo).sum()), 'cert_sim': int(m.cert.sum()),
          'horas_total': float(m.h.sum()), 'horas_media_ativos': round(float(m[m.ativo].h.mean()), 1),
          'horas_mediana_ativos': float(m[m.ativo].h.median()), 'horas_max': float(m.h.max())}
    mm['taxa_ativacao'] = pct(mm['ativos'], mm['total'])
    mm['taxa_cert_total'] = pct(mm['cert_sim'], mm['total'])
    mm['taxa_cert_ativos'] = pct(mm['cert_sim'], mm['ativos'])
    by_opp = {}
    for o in ['Titular', 'Suplente', 'Sem classificação']:
        g = m[m.Opp == o]
        by_opp[o] = {'n': len(g), 'ativos': int(g.ativo.sum()), 'zero_h': int((~g.ativo).sum()), 'cert': int(g.cert.sum()),
                     'horas_media_ativos': round(float(g[g.ativo].h.mean()), 1) if g.ativo.any() else None,
                     'pct_ativos': pct(int(g.ativo.sum()), len(g)), 'pct_cert': pct(int(g.cert.sum()), len(g))}
    mm['por_oportunidade'] = by_opp
    by_t = {}
    for t in ['SP', 'PE', 'DF', 'BA', 'RN']:
        g = m[m['Território'] == t]
        by_t[t] = {'n': len(g), 'titulares': int((g.Opp == 'Titular').sum()), 'suplentes': int((g.Opp == 'Suplente').sum()),
                   'ativos': int(g.ativo.sum()), 'zero_h': int((~g.ativo).sum()), 'cert': int(g.cert.sum()), 'horas': float(g.h.sum()),
                   'horas_media_ativos': round(float(g[g.ativo].h.mean()), 1) if g.ativo.any() else None,
                   'pct_ativos': pct(int(g.ativo.sum()), len(g)), 'pct_cert': pct(int(g.cert.sum()), len(g))}
    mm['por_territorio'] = by_t
    bins = [(0, 0, '0h'), (0.5, 4, 'Até 4h'), (4.5, 9, '4,5 a 9h'), (9.5, 14, '9,5 a 14h'), (14.5, 99, '14,5h ou mais')]
    hb = []
    for lo, hi, lab in bins:
        g = m[(m.h >= lo) & (m.h <= hi)]
        hb.append({'faixa': lab, 'n': len(g), 'cert': int(g.cert.sum()), 'n_sem_cert': int((~g.cert).sum())})
    mm['faixas_horas'] = hb
    mm['cert_regra'] = {'min_horas_com_cert': float(m[m.cert].h.min()), 'max_horas_sem_cert': float(m[~m.cert].h.max()),
                        'sem_cert_com_9_5_ou_mais': int(((~m.cert) & (m.h >= 9.5)).sum()),
                        'cert_com_menos_de_10h': int((m.cert & (m.h < 10)).sum())}
    mm['estado_diferente_do_territorio'] = int((m['Estado'].notna() & (m['Estado'] != m['Território'])).sum())
    mm['sem_estado'] = int(m['Estado'].isna().sum())
    mm['sem_email'] = int(m['E-mail'].isna().sum())
    # cruzamento com inscrições
    mm['localizados_na_base_inscricoes'] = int(m.in_db.sum())
    mm['nao_localizados'] = int((~m.in_db).sum())
    loc = m[m.in_db].copy()
    def best_row(ix):
        sub = db.loc[ix]
        pref = sub[sub['Tipo Inscrição'] == 'Mentorias']
        return (pref if len(pref) else sub).iloc[0]
    br = loc['db_idx'].map(best_row)
    loc['gen'] = br.map(lambda r: r['Gênero']); loc['raca'] = br.map(lambda r: r['Cor/Raça']); loc['form'] = br.map(lambda r: r['Formação'])
    loc['ncat'] = loc['db_idx'].map(lambda ix: db.loc[ix, 'Tipo Inscrição'].nunique())
    loc['cats'] = loc['db_idx'].map(lambda ix: sorted(db.loc[ix, 'Tipo Inscrição'].unique().tolist()))
    loc['score'] = loc['nm'].map(lambda n: resumo.loc[resumo.nm == n, 'Total'].max() if (resumo.nm == n).any() else np.nan)
    loc['uf_db'] = br.map(lambda r: r['UF'])
    mm['perfil_localizados'] = {
        'n': len(loc),
        'mulher': {'n': int(loc.gen.isin(['Mulher Cis', 'Mulher Trans', 'Pessoa não binária']).sum()), 'd': int(loc.gen.notna().sum())},
        'pp': {'n': int(loc.raca.isin(['Preta', 'Parda', 'Indígena']).sum()), 'd': int(loc.raca.notna().sum())},
        'superior': {'n': int(loc.form.isin(['Pós-graduação', 'Ensino Superior (completo)']).sum()), 'd': int(loc.form.notna().sum())},
        'multi_modalidade': {'n': int((loc.ncat > 1).sum()), 'd': len(loc)},
    }
    mm['categorias_localizados'] = {c: int(loc.cats.map(lambda cs: c in cs).sum()) for c in ['Produtores', 'Mentorias', 'Facilitadores', 'Pesquisadores']}
    # pontuação x desfecho
    base_scores = resumo[(resumo['Status Inscrição Detalhado'] == 'Enviada')].drop_duplicates('nm')['Total']
    sc = loc.dropna(subset=['score'])
    sc_nonact = sc[~sc.ativo]; sc_act = sc[sc.ativo]
    mm['pontuacao'] = {
        'n_com_pontuacao': len(sc), 'mediana_convocados': float(sc.score.median()), 'mediana_todos_enviados': float(base_scores.median()),
        'n_todos_enviados': int(len(base_scores)),
        'mediana_titulares': float(sc[sc.Opp == 'Titular'].score.median()), 'mediana_suplentes': float(sc[sc.Opp == 'Suplente'].score.median()),
        'mediana_ativos': float(sc_act.score.median()), 'mediana_zero_h': float(sc_nonact.score.median()),
        'corr_pontuacao_horas': round(float(sc[['score', 'h']].corr(method='spearman').iloc[0, 1]), 2),
        'pct_convocados_acima_mediana_base': pct(int((sc.score > base_scores.median()).sum()), len(sc)),
    }
    # mentorias por categoria de origem na inscrição (quem entrou: só Mentorias vs multi)
    mm['multi_vs_so_mentorias'] = {
        'so_mentorias': {'n': int((loc.ncat == 1).sum()), 'ativos': int(loc[loc.ncat == 1].ativo.sum()), 'cert': int(loc[loc.ncat == 1].cert.sum())},
        'multi': {'n': int((loc.ncat > 1).sum()), 'ativos': int(loc[loc.ncat > 1].ativo.sum()), 'cert': int(loc[loc.ncat > 1].cert.sum())}}
    # convocação: dos inscritos enviados em Mentorias, quantos chegaram à mentoria
    dm = db[(db['Tipo Inscrição'] == 'Mentorias') & (db['Status Inscrição Detalhado'] == 'Enviada')].drop_duplicates('cpf')
    conv_cpf = set(loc['db_cpf'].dropna())
    mm['funil_mentorias'] = {'inscritos_enviados': len(dm), 'convocados_localizados': int(dm.cpf.isin(conv_cpf).sum())}
    res['mentorias'] = mm

    # ---------------- TRILHA ----------------
    ap = person_table(a)  # pessoas únicas nas aulas (todas as inscrições)
    ap_env = person_table(a[a.status_g == 'enviada'])
    db_cpfs = set(db['cpf'].dropna()); db_env = set(db[db['Status Inscrição Detalhado'] == 'Enviada']['cpf'].dropna())
    ap_env = ap_env.copy()
    ap_env['in_db'] = ap_env.cpf.isin(db_cpfs)
    ap_env['part'] = ap_env.n_aulas > 0
    ap_env['cert'] = (ap_env['CERTIFICADO'] == 'Sim')
    ap_env['tem_pres'] = ap_env.terr.map(lambda t: planned.get(t, 0) > 0)  # RN: base só com inscrições
    aulas_cpf_all = set(ap_env.cpf)
    # mentorias <-> aulas (email / nome)
    a_by_em = {r.em: r.cpf for r in ap_env.itertuples() if r.em and r.em != 'nan'}
    a_by_nm = {r.nm: r.cpf for r in ap_env.itertuples()}
    m['aulas_cpf'] = [a_by_em.get(r.em) or a_by_nm.get(r.nm) for r in m.itertuples()]
    m['in_aulas'] = m['aulas_cpf'].notna()
    both_cpf = {r.aulas_cpf for r in m.itertuples() if r.aulas_cpf}
    tr = {}
    tr['inscricoes_original'] = {'pessoas': int(db['cpf'].nunique()), 'enviadas': len(db_env)}
    tr['aulas'] = {'pessoas_enviadas': len(ap_env), 'participantes': int(ap_env.part.sum()), 'cert': int(ap_env[ap_env.terr.isin(['SP', 'DF'])].cert.sum()),
                   'participantes_sp_df': int(ap_env[ap_env.terr.isin(['SP', 'DF'])].part.sum())}
    ov = ap_env[ap_env.in_db]
    tr['aulas_na_base_original'] = {'pessoas': len(ov), 'participantes': int(ov.part.sum()),
                                    'taxa_participacao': pct(int(ov.part.sum()), int(ov.tem_pres.sum()))}
    nv = ap_env[~ap_env.in_db]
    tr['aulas_novos_inscritos'] = {'pessoas': len(nv), 'participantes': int(nv.part.sum()), 'taxa_participacao': pct(int(nv.part.sum()), int(nv.tem_pres.sum()))}
    tr['mentorias'] = {'pessoas': len(m), 'ativos': int(m.ativo.sum()), 'cert': int(m.cert.sum()), 'na_base_original': int(m.in_db.sum())}
    tr['interseccoes'] = {
        'original_e_aulas': int(len(ov)), 'original_e_mentorias': int(m.in_db.sum()), 'aulas_e_mentorias': int(m.in_aulas.sum()),
        'original_aulas_mentorias': int((m.in_aulas & m.in_db & m.aulas_cpf.isin(db_cpfs)).sum()),
        'aulas_e_mentorias_participaram': int((m.in_aulas & m.ativo & m.aulas_cpf.map(lambda c: bool(ap_env.set_index('cpf').part.get(c, False)) if c else False)).sum()),
    }
    # pessoas ativas em >=2 formatos formativos (aulas, mentorias)
    tr['multi_formato'] = {'aulas_e_mentoria_ativas': tr['interseccoes']['aulas_e_mentorias_participaram']}
    # equipe local (15 selecionados): onde aparecem
    team = ['renata maysa abreu da costa', 'neusinea maciel miranda', 'loba makua', 'gislene sousa dos santos costa', 'joesile gomes cordeiro',
            'anny kesia guedes baracho', 'tatiane cristina fernandes', 'jennifer katarina miranda da silva', 'fabiana nascimento',
            'katiuscia marques da silva', 'juliana santos da silva', 'lorena de oliveira elias', 'mariana passos',
            'glaucio teixeira da camara', 'cristiane de almeida santos']
    team_aulas = ap_env[ap_env.nm.isin(team)]
    team_ment = m[m.nm.isin(team)]
    tr['equipe_local'] = {'total': 15, 'em_aulas_inscritos': int(team_aulas.cpf.nunique()), 'em_aulas_participaram': int(team_aulas[team_aulas.part].cpf.nunique()),
                          'em_mentorias': int(team_ment.nm.nunique()), 'em_mentorias_ativas': int(team_ment[team_ment.ativo].nm.nunique()),
                          'em_algum': int(len(set(team_aulas.nm) | set(team_ment.nm)))}

    # funil dos mentorandos localizados na base original
    locm = m[m.in_db]
    unl = m[~m.in_db]
    tr['mentorias_localizados'] = {'n': len(locm), 'ativos': int(locm.ativo.sum()), 'cert': int(locm.cert.sum())}
    tr['mentorias_nao_localizados'] = {'n': len(unl), 'ativos': int(unl.ativo.sum()), 'cert': int(unl.cert.sum())}
    tr['mentorias_funil_base'] = {'inscritos_enviados': mm['funil_mentorias']['inscritos_enviados'],
                                  'convocados': mm['funil_mentorias']['convocados_localizados']}
    # pessoas ativas em formatos formativos (aulas e/ou mentorias)
    tr['ativos_formativos'] = {'aulas': int(ap_env.part.sum()), 'mentorias': int(m.ativo.sum()),
                               'ambos': tr['interseccoes']['aulas_e_mentorias_participaram']}
    tr['ativos_formativos']['uniao'] = tr['ativos_formativos']['aulas'] + tr['ativos_formativos']['mentorias'] - tr['ativos_formativos']['ambos']

    # perfil por etapa (mesmas definições do painel de inscrições; denominador = respondentes)
    def perfil(df, g, r, f):
        gg = df[df[g].notna()]; rr = df[df[r].notna()]; ff = df[df[f].notna()]
        return {'n': len(df),
                'mulher': {'n': int(gg[g].isin(['Mulher Cis', 'Mulher Trans', 'Pessoa não binária']).sum()), 'd': len(gg)},
                'pp': {'n': int(rr[r].isin(['Preta', 'Parda', 'Indígena']).sum()), 'd': len(rr)},
                'superior': {'n': int(ff[f].isin(['Pós-graduação', 'Ensino Superior (completo)']).sum()), 'd': len(ff)}}
    dbp = db[db['Status Inscrição Detalhado'] == 'Enviada'].drop_duplicates('cpf')
    dbm = dm  # candidatos Mentorias enviados (únicos)
    loc_act = loc[loc.ativo]
    apx = ap_env.copy()
    tr['perfil_etapas'] = {
        'inscricoes_original': perfil(dbp, 'Gênero', 'Cor/Raça', 'Formação'),
        'mentorias_candidatos': perfil(dbm, 'Gênero', 'Cor/Raça', 'Formação'),
        'mentorias_convocados': perfil(loc.assign(G=loc.gen, R=loc.raca, F=loc.form), 'G', 'R', 'F'),
        'mentorias_ativos': perfil(loc_act.assign(G=loc_act.gen, R=loc_act.raca, F=loc_act.form), 'G', 'R', 'F'),
        'aulas_inscritos': perfil(apx, 'Gênero', 'Cor/Raça', 'Formação'),
        'aulas_participantes': perfil(apx[apx.part], 'Gênero', 'Cor/Raça', 'Formação'),
    }

    # visão territorial (UF)
    ufs = ['SP', 'PE', 'DF', 'BA', 'RN']
    env_db = db[db['Status Inscrição Detalhado'] == 'Enviada'].copy()
    env_db['UFn'] = env_db['UF'].str.upper().str.strip()
    terr = {}
    for u in ufs:
        a_u = ap_env[ap_env.terr == u]
        w_u = next((x for x in wk['ufs'] if x['uf'] == u), None)
        terr[u] = {
            'inscritos_originais': int(env_db[env_db.UFn == u].cpf.nunique()),
            'aulas_inscritos': res['aulas'][u]['pessoas_enviadas'] if u in res['aulas'] else 0,
            'aulas_participantes': res['aulas'][u]['participantes'] if u in res['aulas'] else 0,
            'workshops_respostas': w_u['n'] if w_u else 0, 'workshops_localidades': w_u['localidades'] if w_u else 0,
            'mentorias_ativos': int(m[(m['Território'] == u) & m.ativo].shape[0]), 'mentorias_total': int(m[m['Território'] == u].shape[0]),
        }
    tr['territorio'] = terr
    res['trilha'] = tr
    res['qualidade'] = {
        'aulas_cpfs_duplicados_mesmo_territorio': res['aulas']['cpfs_duplicados_no_mesmo_territorio'],
        'aulas_idade_campo_invalido': res['aulas']['idade_campo_invalido'],
        'colunas_sem_preenchimento_aulas': ['Remanescentes', 'Selecionados', 'Tem certificado'],
    }
    return res


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--exec', required=True); ap.add_argument('--db', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--keep-samples', action='store_true', help='mantém textos livres (somente para revisão local)')
    ap.add_argument('--html', help='formacoes.html a atualizar: substitui o bloco <script id="dados"> pelo JSON calculado')
    args = ap.parse_args()
    res = build(args)
    if not args.keep_samples:
        for k in list(res['workshops']):
            if k.startswith('_amostra'): del res['workshops'][k]
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(py(res), f, ensure_ascii=False, indent=1)
    print('ok ->', args.out)
    if args.html:
        payload = json.dumps(py(res), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
        with open(args.html, encoding='utf-8') as f:
            page = f.read()
        pat = re.compile(r'(<script id="dados" type="application/json">)(.*?)(</script>)', re.S)
        if not pat.search(page):
            raise SystemExit('bloco <script id="dados"> não encontrado em ' + args.html)
        page = pat.sub(lambda mo: mo.group(1) + payload + mo.group(3), page, count=1)
        with open(args.html, 'w', encoding='utf-8') as f:
            f.write(page)
        print('ok -> html atualizado:', args.html)
