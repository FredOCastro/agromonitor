name: Monitor Diário — Agro Monitor

on:
  schedule:
    # Roda todo dia às 7h horário de Brasília (10h UTC)
    - cron: '0 10 * * *'
  # Permite rodar manualmente pelo botão no GitHub
  workflow_dispatch:

jobs:
  monitorar:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # Necessário para fazer commit e push
      pages: write
      id-token: write

    steps:
      - name: Baixar repositório
        uses: actions/checkout@v4

      - name: Configurar Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Instalar dependências
        run: pip install -r requirements.txt

      - name: Coletar dados externos
        run: python src/fetch_data.py

      - name: Analisar com Claude
        run: python src/analyze.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      - name: Gerar dashboard HTML
        run: python src/generate_dashboard.py

      - name: Enviar alerta se necessário
        run: python src/send_alert.py
        env:
          SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
          EMAIL_DESTINO:    ${{ secrets.EMAIL_DESTINO }}
          EMAIL_REMETENTE:  ${{ secrets.EMAIL_REMETENTE }}

      - name: Salvar arquivos atualizados no repositório
        run: |
          git config user.name "Agro Monitor Bot"
          git config user.email "bot@agro-monitor"
          git add src/data_atual.json src/analise.json src/state.json dashboard/index.html
          git diff --staged --quiet || git commit -m "Monitor diário: $(date '+%d/%m/%Y %H:%M')"
          git push
