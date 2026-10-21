# Criadores Cristãos — observatório Instagram

Teste **sem custos e sem utilizar o Mac** com GitHub Actions para ler apenas informações que o Instagram publica anonimamente nas páginas de Reels. Não descarrega vídeos, não utiliza palavras-passe, contas Meta, proxies nem serviços pagos.

**Estado do teste (21/10/2026):** o primeiro pedido HTTP a partir do runner GitHub foi bloqueado pelo Instagram com HTTP 429. Uma tentativa com Chrome na linha de comandos não devolveu conteúdo. Está a ser testada uma última variante com Playwright; a versão automática diária permanece **desligada** para não repetir pedidos bloqueados. Não há números Instagram verificados publicados.

- Recolha: `scripts/public_instagram.py` (até 12 Reels públicos recentes por perfil)
- Teste Playwright: `scripts/browser_probe.py` (um perfil, sem login)
- Workflow: `.github/workflows/instagram-reels.yml`
- Saída de cada teste: artefacto GitHub Actions com diagnóstico honesto; uma amostra só é publicada em `data/instagram-public.json` se os números forem efetivamente encontrados.

O workflow pode ser lançado manualmente em **Actions → Instagram publico — teste gratuito → Run workflow**, mas não tem agenda diária até passar o teste. Os dados de Reels recentes nunca representam o total histórico de cada conta.

A VPS do observatório permanece independente. O Instagram pode restringir o acesso a partir de servidores cloud; nesse caso não vamos inventar números nem insistir nos pedidos.
