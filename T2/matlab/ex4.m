t = linspace(0, 2/60, 4000); t1 = deg2rad(45)/377;
A = 18.8*sin(deg2rad(45)-0.986)*(1+exp(-pi/377/4e-3))/(1-exp(-pi/377/4e-3));
io = 18.8*sin(377*mod(t-t1,pi/377)+deg2rad(45)-0.986) + A*exp(-mod(t-t1,pi/377)/4e-3);
vo = abs(io>1e-9).*509.*sin(377*t);
plot(t*1e3, vo); xlabel('t (ms)'); ylabel('v_o (V)'); grid on;
figure; plot(t*1e3, io); xlabel('t (ms)'); ylabel('i_o (A)'); grid on;
