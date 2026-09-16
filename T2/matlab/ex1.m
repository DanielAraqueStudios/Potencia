t = linspace(0, 1/60, 2000);
vo = 530*cos(mod(377*t+pi/6, pi/3) - pi/6);
plot(t*1e3, vo); xlabel('t (ms)'); ylabel('v_o (V)'); grid on;
io = vo/96;
figure; plot(t*1e3, io); xlabel('t (ms)'); ylabel('i_o (A)'); grid on;
