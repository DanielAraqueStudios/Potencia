Vm=509.12; w=376.991; Im=18.76; phi=0.98; alpha=deg2rad(90); tau=4e-3;
t1=alpha/w; I0=-Im*sin(alpha-phi); T=1/60;
t=linspace(0,4*T,4000); thetaLocal=mod(t-t1,pi/w);
io=max(Im*sin(w*thetaLocal+alpha-phi)+I0*exp(-thetaLocal/tau),0);
plot(t*1e3,io,'r','LineWidth',1.2); hold on
title('Corriente de salida del rectificador (simulacion)')
xlabel('Tiempo (ms)'); ylabel('Corriente (A)')
grid on
