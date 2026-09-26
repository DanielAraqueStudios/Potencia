x=linspace(0.0041667,0.01063,200);
io=18.76*sin(376.991*x-0.98)-10.45*exp(-250*(x-0.0041667));
plot(x*1e3,io,'r','LineWidth',1.5); hold on
title('Corriente de salida io(t)'); xlabel('Tiempo (ms)'); ylabel('Corriente (A)')
grid on
