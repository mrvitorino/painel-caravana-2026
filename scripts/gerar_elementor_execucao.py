#!/usr/bin/env python3
"""Gera wordpress/painel-execucao-2026-elementor.html a partir de formacoes.html.

Aplica as regras do CLAUDE.md para colar no widget HTML do Elementor:
CSS escopado sob #cv2026-execucao, @keyframes renomeado, header (logo) e footer
(régua) removidos, breakpoints mobile, arquivo único sem DOCTYPE/html/head/body.

Uso: python3 scripts/gerar_elementor_execucao.py [formacoes.html] [saida.html]
"""
import re
import sys

WRAP = '#cv2026-execucao'
src = sys.argv[1] if len(sys.argv) > 1 else 'formacoes.html'
dst = sys.argv[2] if len(sys.argv) > 2 else 'wordpress/painel-execucao-2026-elementor.html'
page = open(src, encoding='utf-8').read()


def block(tag, text, attrs=''):
    m = re.search(r'<%s%s>(.*?)</%s>' % (tag, attrs, tag), text, re.S)
    if not m:
        raise SystemExit('bloco <%s> não encontrado' % tag)
    return m.group(1)


css = block('style', page)
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)


def split_blocks(s):
    """Itera (cabeçalho, corpo) dos blocos de nível superior de um CSS."""
    i, n = 0, len(s)
    while i < n:
        j = s.find('{', i)
        if j < 0:
            break
        head = s[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            depth += {'{': 1, '}': -1}.get(s[k], 0)
            k += 1
        yield head, s[j + 1:k - 1]
        i = k


def prefix_selector(sel):
    sel = sel.strip()
    if sel in (':root', 'html', 'body'):
        return WRAP
    if sel.startswith(('body ', 'html ')):
        sel = sel.split(' ', 1)[1]
    return '%s %s' % (WRAP, sel)


def scope(s):
    out = []
    for head, body in split_blocks(s):
        if head.startswith('@keyframes'):
            out.append('%s {%s}' % (head.replace('fadeIn', 'cv2026FadeIn'), body))
        elif head.startswith('@media'):
            out.append('%s {\n%s\n}' % (head, scope(body)))
        else:
            sels = ', '.join(prefix_selector(x) for x in head.split(','))
            out.append('%s {%s}' % (sels, body))
    return '\n'.join(out)


scoped = scope(css).replace('animation: fadeIn', 'animation: cv2026FadeIn')
assert 'fadeIn' not in scoped.replace('cv2026FadeIn', ''), 'referência a fadeIn sem prefixo'

mobile = '''
%(w)s { max-width: 100%%; }
%(w)s h1, %(w)s h2, %(w)s h3, %(w)s h4, %(w)s p, %(w)s table, %(w)s li { font-family: inherit; text-transform: none; }
%(w)s header { height: auto; }
%(w)s header { flex-wrap: wrap; row-gap: 10px; }
@media (max-width: 600px) {
    %(w)s header { padding: 16px 18px; }
    %(w)s header h1 { font-size: 18px; }
    %(w)s header .subtitle { font-size: 11px; }
    %(w)s .container { width: 96%%; margin: 20px auto; }
    %(w)s .section-head h2 { font-size: 21px; }
    %(w)s .card .value { font-size: 26px; }
    %(w)s .stat-tile .st-value { font-size: 24px; }
    %(w)s .callout { padding: 18px; }
    %(w)s .callout .co-num { font-size: 26px; min-width: 70px; }
    %(w)s .chart-wrapper.xs { height: 150px; }
    %(w)s .chart-wrapper.xl { height: 300px; }
    %(w)s table.datatable { font-size: 13px; }
}
''' % {'w': WRAP}

body = block('body', page)
wrapper = re.search(r'<div id="cv2026-execucao">.*</div>(?=\s*<script id="dados")', body, re.S).group(0)
wrapper = re.sub(r'\s*<footer>.*?</footer>', '', wrapper, flags=re.S)                    # regra 4: sem footer
wrapper = re.sub(r'\s*<img src="LogoCaravanaWhite\.png"[^>]*>', '', wrapper)              # regra 4: sem logo
wrapper = re.sub(r'<a class="nav-link" href="index\.html">',
                 '<a class="nav-link" href="https://caravana.culturaemercado.com.br/inscricoes-impacto-2026/">', wrapper)
dados = re.search(r'<script id="dados" type="application/json">.*?</script>', body, re.S).group(0)
logic = re.search(r'</script>\s*<script>(.*)</script>\s*$', body.strip(), re.S).group(1)
assert 'getElementById(\'cv2026-execucao\')' in logic

out = '''<!-- ===== INICIO: Painel de Execução 2026 (adaptado para Elementor/WordPress) ===== -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Barlow:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
%s
%s
</style>
%s
%s
<script>%s</script>
<!-- ===== FIM: Painel de Execução 2026 ===== -->
''' % (scoped, mobile, wrapper, dados, logic)

open(dst, 'w', encoding='utf-8').write(out)
print('ok ->', dst, len(out), 'bytes')
