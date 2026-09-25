Uma ferramenta lê arquivos de uma pasta e o modelo escolhe qual. Como qualquer entrada vinda do modelo, isso não é confiável.

Implemente `safe_read(root, relative_path)`:

- `root` é a pasta permitida (`Path`), e `relative_path` é o que o modelo pediu (string)
- Devolve o conteúdo do arquivo como texto (UTF-8)
- Se o caminho escapar de `root` (por exemplo `../../.env`, ou um caminho absoluto), levante `PermissionError`
- Se o arquivo não existir dentro de `root`, levante `FileNotFoundError`

O teste inclui um arquivo sensível fora da raiz. Ele não pode ser lido de jeito nenhum.
