x=linspace(0.0041667,0.01063,200);
vo=509.12*sin(376.991*x);
plot(x*1e3,vo,'b','LineWidth',1.5); hold on
title('Tension de salida vo(t)'); xlabel('Tiempo (ms)'); ylabel('Tension (V)')
grid on
