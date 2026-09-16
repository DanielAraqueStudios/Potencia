t = linspace(0, 1/50, 2000); w = 100*pi; Vm = 611/sqrt(3);
vo = max(max(Vm*sin(w*t), Vm*sin(w*t-2*pi/3)), Vm*sin(w*t+2*pi/3));
plot(t*1e3, vo); xlabel('t (ms)'); ylabel('v_o (V)'); grid on;
io = vo/96;
figure; plot(t*1e3, io); xlabel('t (ms)'); ylabel('i_o (A)'); grid on;
