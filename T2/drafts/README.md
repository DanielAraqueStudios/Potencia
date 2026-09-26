# Ejercicio 4 (variante) — Rectificador controlado, R=15Ω, L=38mH

Basado en el ejercicio 4 de la imagen `33db571f-9356-4c95-add5-e78f47357efd.jpg`
(rectificador controlado tipo puente, alimentado con Vs = 250·sen(120πt) V, α = 20°),
resuelto con los valores R = 15 Ω y L = 38 mH.

## Datos

- Vs = 250·sen(120πt) V
- α = 20° = π/9 rad ; π+α = 3,491 rad
- R = 15 Ω, L = 38 mH

## Impedancia de carga y corriente forzada

ωL = 120π·0,038 = 14,326 Ω
Z = 15 + j14,326 = 20,7419 Ω ∠0,7624 rad (43,6827°)

I_f = 250∠0 / 20,7419∠0,7624 = 12,0529 A ∠−0,7624

i(t) = 12,0529·sen(120πt − 0,7624) + Io·e^(−t/τ)

## a) Tipo de corriente

τ = L/R = 0,038/15 = 2,533 ms → 1/τ = 394,7 s⁻¹

t₁ = α/ω = 0,9258 ms

**Condición inicial (i(t₁)=0):**
0 = 12,0529·sen(0,349066−0,7624) + Io → Io = 4,8413 A

**Condición final** (cruce por cero después de π+α):

0 = 12,0529·sen(120πtc − 0,7624) + 4,8413·e^(−394,7(tc−0,000926))
→ tc ≈ 10,38 ms

β = 120π·tc = 3,91 rad

Como β (3,91 rad) > π+α (3,49 rad) → **la corriente es continua**.

## b) Corrientes y tensiones DC y RMS (por armónicos)

**Para n=0, f=0 (componente DC):**

V_DC = (1/π)·∫_(π/9)^3,49rad 250·sen(θ) dθ = (250/π)·[−cos(θ)]_(π/9)^3,49rad = (250/π)·[−cos(3,49)+cos(π/9)] = **149,6 V**

I_DC = V_DC/R = 149,6/15 = **9,97 A**

**Para n=2, f=120Hz:**

Z₂ = 15 + j240π rad/s·(0,038) = 32,34 Ω∠1,089

a₂ = 2(250)/π·[cos(3π/9)/3 − cos(π/9)/1] = **−123 V**

b₂ = 2(250)/π·[sen(3π/9)/3 − sen(π/9)/1] = **−8,49 V**

V₂ = √[(−123)² + (−8,49)²] = **123,3 V**

|I₂| = 123,3/32,34 = **3,81 A**

Los demás aₙ, bₙ (n=4,6,8,10,12,14) se obtienen igual, cambiando (n+1) y (n−1);
son iguales a los del ejercicio base porque V_DC, aₙ, bₙ solo dependen de Vs y α,
no de R ni L. Con estos valores y Zₙ = 15 + j·n·120π·0,038 se arma la tabla:

| n | aₙ (V) | bₙ (V) | Vₙ (V) | Zₙ (Ω∠rad) | Iₙ (A) |
|---|--------|--------|--------|------------|--------|
| 0 | — | — | 149,6 | 15 | I_DC = 9,97 |
| 2 | −123 | −8,49 | 123,3 | 32,34∠1,089 | 3,81 |
| 4 | −32,1 | −14,6 | 35,3 | 59,24∠1,315 | 0,596 |
| 6 | −11,9 | −16,7 | 20,5 | 87,26∠1,397 | 0,235 |
| 8 | −0,266 | −14,6 | 14,6 | 115,6∠1,441 | 0,126 |
| 10 | 6,60 | −9,3 | 11,4 | 144,1∠1,466 | 0,0791 |
| 12 | 8,96 | −2,76 | 9,38 | 172,6∠1,484 | 0,0544 |
| 14 | 7,43 | 2,87 | 7,97 | 201,1∠1,496 | 0,0396 |

**Tensiones (iguales al problema base, no dependen de R,L):**
- V_DC = 149,6 V
- V_RMS = √[(149,6)² + ((123,3)² + (35,3)² + (20,5)² + (14,6)² + (11,4)² + (9,38)² + (7,97)²)/2] = 176,2 V

**Corrientes (nuevas, con R=15Ω, L=38mH):**
- I_DC = 9,97 A
- I_RMS = √[(9,97)² + ((3,81)² + (0,596)² + (0,235)² + (0,126)² + (0,0791)² + (0,0544)² + (0,0396)²)/2] = 10,34 A

## c) Potencias

- P (activa, en R) = I_RMS²·R = 10,34²·15 = 1604,2 W
- P_DC = V_DC·I_DC = 149,6·9,97 = 1492,0 W
- S (aparente) = V_s,RMS·I_RMS = 177·10,34 = 1830,2 VA

## d) Factor de potencia y eficiencia

- FP = P/S = 1604,2/1830,2 = 0,877
- η = P_DC/S = 1492,0/1830,2 = 0,815

## e) Factores de rizo

- FRV = √(V_RMS² − V_DC²)/V_DC = √(176,2² − 149,6²)/149,6 = 0,622
- FRI = √(I_RMS² − I_DC²)/I_DC = √(106,9 − 99,46)/9,97 = 0,274

## Expresiones finales

v(t) = 149,6 − 123·cos(240πt) − 8,49·sen(240πt) − 32,1·cos(480πt) − 14,6·sen(480πt)
       − 11,9·cos(720πt) − 16,7·sen(720πt) + ...

i(t) = 9,97 − 3,80·cos(240πt−1,089) − 0,262·sen(240πt−1,089)
       − 0,542·cos(480πt−1,315) − 0,246·sen(480πt−1,315) + ...
