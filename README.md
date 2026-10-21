# Criadores Cristãos — observatório Instagram

Este repositório executa uma experiência de recolha **gratuita**, por GitHub Actions, de contagens públicas de Reels de perfis do observatório [Criadores Cristãos em Portugal](https://criadores.109-205-177-192.sslip.io/).

**Sem login Instagram, sem passwords, sem compra de APIs e sem usar o Mac.** São lidas exclusivamente informações disponibilizadas anonimamente pelas páginas públicas. O Instagram pode bloquear ou omitir os dados; nessas situações o sistema **não inventa números**.

- Código: `scripts/public_instagram.py`
- Workflow: `.github/workflows/instagram-reels.yml`
- Resultados públicos gerados, caso existam: `data/instagram-public.json`
- Dados representados: seguidores disponíveis, contagem de Reels observados e visualizações/gostos dos até **12 Reels recentes** por perfil; isto **não** é o total histórico da conta.
- O workflow corre uma vez por dia e também pode ser iniciado manualmente na aba **Actions**.

O GitHub Actions tem quotas, e a recolha pode falhar quando o Instagram recusa tráfego de servidores cloud. Não se deve confundir um teste de leitura bem-sucedido num navegador local com a disponibilidade num runner do GitHub.

Segredos e tokens não pertencem ao repositório: o relatório publicado contém apenas contagens públicas e identificadores públicos dos posts. A integração final com a VPS será feita somente depois de validarmos os resultados no runner.
