Como a mesma entrada pode gerar saídas diferentes, avaliar um caso uma vez só não mede nada. Escreva `evaluate(run, cases, repetitions)`.

- `run` é uma função que recebe a entrada de um caso e devolve a saída do sistema
- `cases` é uma lista de tuplas `(input, expected)`
- `repetitions` é quantas vezes rodar **cada** caso

Devolva um dicionário:

- `"pass_rate"`: proporção de execuções corretas sobre o total de execuções (float)
- `"per_case"`: lista com a taxa de acerto de cada caso, na ordem de `cases`
- `"unstable"`: lista dos índices dos casos que às vezes acertam e às vezes erram
- `"runs"`: número total de execuções

Com `cases` vazia, devolva `pass_rate` igual a `0.0` e as listas vazias. `repetitions` menor que 1 levanta `ValueError`.
