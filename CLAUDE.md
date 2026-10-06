# Painel Caravana Energia da Cultura 2026

Painel estático de inscrições, seleção de talentos locais e relatório institucional
da Caravana Energia da Cultura 2026 (patrocínio Neoenergia).

## Publicação — dois destinos, sempre nesta ordem

Toda atualização deste painel é publicada em **dois lugares**. O GitHub é a fonte
da verdade; o WordPress/Elementor é sempre gerado **por último**, a partir do
`index.html` já finalizado.

### 1. GitHub Pages (fonte da verdade)

- Arquivo: `index.html` na raiz deste repositório.
- Deploy automático a cada push na branch `main` (GitHub Pages "Deploy from a
  branch").
- Domínio próprio: `https://marcelvitorino.com.br/painel-caravana-2026`
  (custom domain configurado no repositório `mrvitorino/mrvitorino.github.io`,
  que os projetos herdam por caminho). O link antigo
  `https://mrvitorino.github.io/painel-caravana-2026` redireciona automaticamente.
- Fluxo de trabalho: alterações grandes/estruturais vão numa branch
  `claude/...`, com Pull Request para `main` (revisão + merge, geralmente pelo
  usuário ou com sua confirmação explícita). Ajustes pequenos e sem risco podem
  ir direto para `main`.

### 2. WordPress / Elementor (sempre o último passo)

- Site: https://caravana.culturaemercado.com.br
- CMS: WordPress, construído com **Elementor**.
- Página do painel: https://caravana.culturaemercado.com.br/inscricoes-impacto-2026/
  ("Inscrições & Impacto 2026").
- O conteúdo é colado inteiro num único **widget HTML** do Elementor nessa página.
- Menu: a página está cadastrada como **submenu (subitem)** do item já existente
  "Inteligência Avaliativa", em Aparência → Menus.
- Referência da última versão publicada: `wordpress/painel-caravana-2026-elementor.html`
  neste repositório — use como template/baseline ao gerar a próxima versão.

## Como gerar o HTML do Elementor a partir do `index.html`

Sempre que `index.html` for atualizado, gere uma nova versão do arquivo do
Elementor (`wordpress/painel-caravana-2026-elementor.html`) aplicando estas
transformações — todas necessárias para embutir com segurança dentro do tema
do WordPress sem conflitos:

1. **Escopar todo o CSS sob `#cv2026-painel`** — prefixar cada seletor do
   `<style>` com `#cv2026-painel` (ex: `.card` vira `#cv2026-painel .card`),
   para que classes genéricas (`.container`, `.card`, `.tab`, etc.) não vazem
   nem colidam com estilos do tema WordPress.
2. **Escopar o JS das abas** — a função `openTab` e qualquer
   `querySelectorAll('.tab')` / `.tab-content` devem buscar apenas dentro de
   `document.getElementById('cv2026-painel')`, nunca em `document` inteiro.
3. **Renomear a animação** `@keyframes fadeIn` para `@keyframes cv2026FadeIn`
   (e atualizar a referência em `.tab-content`), evitando colisão de nomes com
   animações do tema.
4. **Remover o `<header>` interno (logo + título de marca) e o `<footer>`
   (régua de patrocinadores/texto institucional)** — o tema do WordPress já
   fornece cabeçalho (com logo) e rodapé (com essas mesmas informações) no
   site, então mantê-los duplicaria a informação. Manter apenas o título
   "Painel de Inscrições & Impacto 2026" e o subtítulo dentro do wrapper.
5. **Manter**: o link da fonte Google Fonts "Barlow" e o
   `<script src="https://cdn.jsdelivr.net/npm/chart.js">` — o Elementor não
   bloqueia CDNs externos.
6. **Adicionar breakpoints extras de responsividade** (`@media (max-width: 600px)`)
   para cabeçalho, títulos, cards e gráficos, cobrindo telas de celular — o
   tema do site pode não dar largura total como o GitHub Pages.
7. Salvar o resultado como um único arquivo autocontido (`<link>` de fonte +
   `<script>` Chart.js + `<style>` + `<div id="cv2026-painel">...</div>` +
   `<script>` de lógica/gráficos), pronto para colar direto no widget HTML do
   Elementor — sem `<!DOCTYPE>`, `<html>`, `<head>` ou `<body>`.

Depois de gerar, commitar o novo `wordpress/painel-caravana-2026-elementor.html`
neste repositório (mesmo commit/PR da atualização do `index.html`) e avisar o
usuário para colar o conteúdo no widget HTML existente na página do Elementor —
publicar no WordPress é uma ação manual do usuário, feita fora do GitHub.

## Dados-fonte

Os dados usados no painel vêm da pasta `data/`:
- `DB_Inscritos_Caravana2026.xlsx` (aba `DB_Inscritos` — base consolidada de inscrições). **Fica apenas na máquina local (ignorada pelo `.gitignore`)**: contém CPF, e-mail e telefone e o repositório é público. Foi removida do repositório e do histórico em 06/10/2026; nunca commitar planilhas com dados pessoais.
- `Pesquisadores_produtores_locais.pdf` (processo de seleção de talentos locais)
- `Metodologia_Escolha_Municipios_Caravana2026.pdf` (metodologia ODS de escolha de municípios)
- `Caravana_Energia_2026_Strategic_Impact.pdf` (histórico, estratégia e eixos de formação)
- `IdentidadeVisual.pdf` (paleta de cores oficial e tipografia — Barlow)

A paleta de cores (`--verde: #009B39`, `--verde-escuro: #12422B`, `--azul: #52A2DA`,
`--laranja: #F59C00`, `--fundo: #FFF9F4`) e a fonte Barlow são oficiais e não devem
ser alteradas sem nova orientação de identidade visual.

## Painel de Execução 2026 (segundo painel, mesmo local de publicação)

Painel das formações executadas: aulas síncronas online (SP, PE, DF, BA), workshops
presenciais, mentorias online, trilha do participante (cruzamento com a base de
inscrições) e relatório institucional. Mesmo design do painel de inscrições.

- **GitHub Pages:** `formacoes.html` na raiz (`.../painel-caravana-2026/formacoes.html`),
  com link cruzado para `index.html` (o `index.html` ainda não aponta para ele).
- **Dados:** `BaseDeDados_Aulas_Workshops_Mentorias.xlsx` (abas BaseSP, BasePE, BaseDF,
  BaseBA, BaseWorkshops, BaseMentorias) + `data/DB_Inscritos_Caravana2026.xlsx`.
  A planilha de formações **não é commitada** (contém dados pessoais); o repositório é
  público, então publique somente agregados.
- **Atualizar números:** `python3 scripts/build_formacoes.py --exec <xlsx> --db data/DB_Inscritos_Caravana2026.xlsx --out /tmp/dados.json --html formacoes.html`
  (só substitui o JSON embutido; o JSON publicado não tem nome, CPF, e-mail nem telefone).
- **Texto narrativo e relatório:** os números do texto são ligados ao JSON (`data-v`), mas a
  interpretação (pontos positivos/melhoria, recomendações, notas de leitura) está escrita à mão
  no HTML — revisar a cada atualização de dados.
- **Cruzamentos:** aulas por CPF; mentorias (sem CPF) por e-mail e, na falta, nome normalizado;
  workshops são formulários anônimos (só análise por território).
- **Elementor:** `python3 scripts/gerar_elementor_execucao.py` gera
  `wordpress/painel-execucao-2026-elementor.html` (wrapper `#cv2026-execucao`, mesmas 7 regras
  acima; a logo, a régua e o rodapé são removidos). Colar num novo widget HTML do Elementor,
  em página própria (sugestão: subitem de "Inteligência Avaliativa", ao lado de "Inscrições & Impacto 2026").
