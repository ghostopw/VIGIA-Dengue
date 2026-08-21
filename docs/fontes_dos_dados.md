# Proveniencia dos dados -- VIGIA-Dengue

Todo dado bruto do projeto veio de API publica, sem autenticacao.
Cada URL abaixo pode ser aberta no navegador e devolve exatamente o
conteudo que gerou o arquivo local correspondente.

## Cadeia de origem

```
SINAN (Ministerio da Saude)
   |  notificacoes de dengue, chikungunya e zika
   v
InfoDengue (Fiocruz + FGV EMAp)
   |  repasse semanal do SINAN; aplica nowcasting do atraso de notificacao
   v
API publica alertcity  -->  dados/bruto/infodengue/ (99 arquivos)
```

## Portais das fontes

| Fonte | Portal | Documentacao |
|---|---|---|
| InfoDengue | https://info.dengue.mat.br | https://info.dengue.mat.br/services/api |
| IBGE -- localidades | https://servicodados.ibge.gov.br/api/docs/localidades | https://servicodados.ibge.gov.br/api/v1/localidades |
| IBGE -- malhas | https://servicodados.ibge.gov.br/api/docs/malhas | https://servicodados.ibge.gov.br/api/v3/malhas |

## Foco do projeto: Brasilia (DF)

| Arbovirose | URL |
|---|---|
| dengue | https://info.dengue.mat.br/api/alertcity?geocode=5300108&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| chikungunya | https://info.dengue.mat.br/api/alertcity?geocode=5300108&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| zika | https://info.dengue.mat.br/api/alertcity?geocode=5300108&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |

## Todas as requisicoes (132)

| Municipio | UF | Fonte | Conteudo | URL |
|---|---|---|---|---|
| Abadiania | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200100&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Abadiania | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200100&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Abadiania | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200100&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Abadiania | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5200100?formato=application/vnd.geo+json&qualidade=intermediaria |
| Agua Fria de Goias | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200175&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Agua Fria de Goias | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200175&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Agua Fria de Goias | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200175&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Agua Fria de Goias | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5200175?formato=application/vnd.geo+json&qualidade=intermediaria |
| Aguas Lindas de Goias | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200258&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Aguas Lindas de Goias | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200258&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Aguas Lindas de Goias | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200258&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Aguas Lindas de Goias | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5200258?formato=application/vnd.geo+json&qualidade=intermediaria |
| Alexania | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200308&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Alexania | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200308&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Alexania | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200308&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Alexania | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5200308?formato=application/vnd.geo+json&qualidade=intermediaria |
| Alto Paraiso de Goias | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200605&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Alto Paraiso de Goias | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200605&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Alto Paraiso de Goias | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200605&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Alto Paraiso de Goias | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5200605?formato=application/vnd.geo+json&qualidade=intermediaria |
| Alvorada do Norte | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200803&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Alvorada do Norte | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200803&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Alvorada do Norte | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5200803&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Alvorada do Norte | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5200803?formato=application/vnd.geo+json&qualidade=intermediaria |
| Barro Alto | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5203203&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Barro Alto | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5203203&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Barro Alto | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5203203&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Barro Alto | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5203203?formato=application/vnd.geo+json&qualidade=intermediaria |
| Brasilia | DF | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5300108&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Brasilia | DF | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5300108&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Brasilia | DF | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5300108&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Brasilia | DF | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5300108?formato=application/vnd.geo+json&qualidade=intermediaria |
| Buritis | MG | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=3109303&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Buritis | MG | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=3109303&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Buritis | MG | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=3109303&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Buritis | MG | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/3109303?formato=application/vnd.geo+json&qualidade=intermediaria |
| Cabeceira Grande | MG | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=3109451&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cabeceira Grande | MG | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=3109451&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cabeceira Grande | MG | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=3109451&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cabeceira Grande | MG | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/3109451?formato=application/vnd.geo+json&qualidade=intermediaria |
| Cabeceiras | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5204003&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cabeceiras | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5204003&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cabeceiras | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5204003&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cabeceiras | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5204003?formato=application/vnd.geo+json&qualidade=intermediaria |
| Cavalcante | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5205307&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cavalcante | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5205307&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cavalcante | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5205307&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cavalcante | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5205307?formato=application/vnd.geo+json&qualidade=intermediaria |
| Cidade Ocidental | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5205497&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cidade Ocidental | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5205497&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cidade Ocidental | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5205497&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cidade Ocidental | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5205497?formato=application/vnd.geo+json&qualidade=intermediaria |
| Cocalzinho de Goias | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5205513&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cocalzinho de Goias | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5205513&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cocalzinho de Goias | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5205513&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cocalzinho de Goias | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5205513?formato=application/vnd.geo+json&qualidade=intermediaria |
| Corumba de Goias | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5205802&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Corumba de Goias | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5205802&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Corumba de Goias | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5205802&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Corumba de Goias | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5205802?formato=application/vnd.geo+json&qualidade=intermediaria |
| Cristalina | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5206206&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cristalina | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5206206&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cristalina | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5206206&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Cristalina | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5206206?formato=application/vnd.geo+json&qualidade=intermediaria |
| Flores de Goias | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5207907&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Flores de Goias | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5207907&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Flores de Goias | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5207907&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Flores de Goias | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5207907?formato=application/vnd.geo+json&qualidade=intermediaria |
| Formosa | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5208004&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Formosa | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5208004&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Formosa | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5208004&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Formosa | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5208004?formato=application/vnd.geo+json&qualidade=intermediaria |
| Goianesia | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5208608&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Goianesia | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5208608&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Goianesia | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5208608&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Goianesia | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5208608?formato=application/vnd.geo+json&qualidade=intermediaria |
| Luziania | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5212501&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Luziania | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5212501&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Luziania | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5212501&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Luziania | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5212501?formato=application/vnd.geo+json&qualidade=intermediaria |
| Mimoso de Goias | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5213053&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Mimoso de Goias | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5213053&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Mimoso de Goias | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5213053&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Mimoso de Goias | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5213053?formato=application/vnd.geo+json&qualidade=intermediaria |
| Niquelandia | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5214606&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Niquelandia | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5214606&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Niquelandia | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5214606&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Niquelandia | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5214606?formato=application/vnd.geo+json&qualidade=intermediaria |
| Novo Gama | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5215231&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Novo Gama | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5215231&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Novo Gama | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5215231&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Novo Gama | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5215231?formato=application/vnd.geo+json&qualidade=intermediaria |
| Padre Bernardo | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5215603&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Padre Bernardo | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5215603&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Padre Bernardo | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5215603&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Padre Bernardo | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5215603?formato=application/vnd.geo+json&qualidade=intermediaria |
| Pirenopolis | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5217302&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Pirenopolis | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5217302&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Pirenopolis | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5217302&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Pirenopolis | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5217302?formato=application/vnd.geo+json&qualidade=intermediaria |
| Planaltina | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5217609&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Planaltina | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5217609&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Planaltina | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5217609&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Planaltina | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5217609?formato=application/vnd.geo+json&qualidade=intermediaria |
| Santo Antonio do Descoberto | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5219753&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Santo Antonio do Descoberto | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5219753&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Santo Antonio do Descoberto | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5219753&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Santo Antonio do Descoberto | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5219753?formato=application/vnd.geo+json&qualidade=intermediaria |
| Sao Joao d'Alianca | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5220009&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Sao Joao d'Alianca | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5220009&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Sao Joao d'Alianca | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5220009&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Sao Joao d'Alianca | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5220009?formato=application/vnd.geo+json&qualidade=intermediaria |
| Simolandia | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5220686&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Simolandia | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5220686&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Simolandia | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5220686&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Simolandia | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5220686?formato=application/vnd.geo+json&qualidade=intermediaria |
| Unai | MG | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=3170404&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Unai | MG | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=3170404&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Unai | MG | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=3170404&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Unai | MG | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/3170404?formato=application/vnd.geo+json&qualidade=intermediaria |
| Valparaiso de Goias | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5221858&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Valparaiso de Goias | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5221858&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Valparaiso de Goias | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5221858&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Valparaiso de Goias | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5221858?formato=application/vnd.geo+json&qualidade=intermediaria |
| Vila Boa | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5222203&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Vila Boa | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5222203&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Vila Boa | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5222203&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Vila Boa | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5222203?formato=application/vnd.geo+json&qualidade=intermediaria |
| Vila Propicio | GO | InfoDengue | dengue: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5222302&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Vila Propicio | GO | InfoDengue | chikungunya: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5222302&disease=chikungunya&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Vila Propicio | GO | InfoDengue | zika: serie municipio-semana 2014-2026 | https://info.dengue.mat.br/api/alertcity?geocode=5222302&disease=zika&format=json&ew_start=1&ew_end=53&ey_start=2014&ey_end=2026 |
| Vila Propicio | GO | IBGE | malha cartografica municipal (GeoJSON) | https://servicodados.ibge.gov.br/api/v3/malhas/municipios/5222302?formato=application/vnd.geo+json&qualidade=intermediaria |

## Como reconferir

Abrir qualquer URL da tabela no navegador, ou:

```bash
curl 'https://info.dengue.mat.br/api/alertcity?geocode=5300108&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2024&ey_end=2024'
```

Para refazer toda a coleta do zero:

```bash
python src/vigia/executar_ingestao.py      # dengue, 33 municipios
python src/vigia/executar_arboviroses.py   # chikungunya e zika
python src/vigia/executar_malha.py         # malha cartografica
```