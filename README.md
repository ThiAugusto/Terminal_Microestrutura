# 🔬 HFT Order Flow & Market Microstructure Terminal

Este repositório contém uma aplicação quantitativa desenvolvida em **Python** e **Streamlit** para análise de microestrutura de mercado e fluxo de ordens de alta frequência (HFT). 

### 🚀 Principais Funcionalidades:
* **Cumulative Volume Delta (CVD):** Acompanhamento do saldo direcional de agressões (Taker Buy vs Taker Sell).
* **Volume Profile & Value Area:** Cálculo dinâmico do *Volume Point of Control* (VPOC) e da faixa de 70% de liquidez institucional.
* **VWAP Institucional:** Linha de preço médio ponderado pelo volume acompanhada por bandas de desvio padrão ($1.2\sigma$).
* **Detector de Ordens Iceberg:** Algoritmo quantitativo para identificar absorções ocultas e defesa passiva de grandes *players*.
