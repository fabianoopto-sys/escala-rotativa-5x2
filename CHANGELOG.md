# Changelog — Escala Rotativa 5×2

## 2.30 — 16/11/2026

Base: 2.29 (blob 97c50223498301c9d4883932aba18dea7d15b33f). Mesmas chaves de armazenamento (`mundial_escalas_v2` e `escala_rotativa_dados_local_2_8`): os dados já salvos continuam válidos.

### Conformidade legal (EC 141/2026)
- Limite semanal automático pela data de cada semana: 44 h até 15/12/2026, 42 h de 16/12/2026 a 15/12/2027 e 40 h a partir de 16/12/2027. A semana que atravessa uma mudança usa o limite mais novo. Também é possível fixar o limite em 44, 42 ou 40 h.
- Jornada diária: até 8 h sem alerta. Até 8h24 na transição gera alerta (liminar do STF nas ADIs 8041/8042, de 12/11/2026, ainda pendente de referendo). Acima disso, só com acordo ou convenção de compensação. Acima de 10 h, a escala é bloqueada.
- Intervalo para refeição (CLT, art. 71) gera alerta. Descanso entre jornadas abaixo de 11 h (CLT, art. 66) bloqueia a escala.
- Regra do domingo no comércio (Lei 10.101/2000, art. 6º): quando a loja abre aos domingos, folga no domingo ao menos 1 vez a cada 3 semanas, ou a cada 2 (quinzenal). Vale no gerador e na validação.
- Nova aba "Lei 5×2 & conformidade": linha do tempo, situação no STF, parâmetros legais e diagnóstico de transição por colaborador.

### Interface
- Faixa com a regra em vigor e a contagem de dias até a próxima etapa.
- Modelos de jornada: 40 h (8h–18h com 2 h; 9h–18h com 1 h) e 42 h (8h–18h com 1h36). O padrão de novo cadastro passa a ser 40 h com 8h–18h e 2 h.
- Atalhos de funcionamento (segunda a sábado; segunda a sexta) e de período (mês atual, próximo mês, 3 meses, transição).
- Calendário compacto: o dia fica separado da contagem de presentes (selo verde) e os nomes de quem folga aparecem em etiquetas. Novo modo Lista, padrão no celular. O calendário do período passa a ser recolhível.

### Correções
- Duas tags `<style>` soltas invalidavam regras de CSS do calendário.
- Escape de HTML em cargos e datas bloqueadas (XSS).
- Datas especiais salvas ou removidas reconferem as semanas futuras automaticamente.
- "Limpar dados locais" baixa um backup antes de apagar.
- Desempenho: cache por renderização. O calendário com 250 pessoas caiu de 4,3 s para 0,24 s.

### Testes
- `testes/e2e_v2_30.py` (Playwright + Chrome, dados fictícios): 34 verificações, todas aprovadas. Cobrem 5×2/F/H, 24/25/26 de dezembro, bloqueio de 44 h após 16/12/2026, regra do domingo, regressão 26/12→01/12, XSS, 250 funcionários e telas de 375/768/1440 px.
- Ainda não testado: iPhone real (Safari), impressão física e uso em várias abas ao mesmo tempo.
