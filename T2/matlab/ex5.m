t = linspace(0, 2/60, 4000); t1 = deg2rad(90)/377;
I0 = -18.8*sin(deg2rad(90)-0.986);
io = max(18.8*sin(377*mod(t-t1,pi/377)+deg2rad(90)-0.986) + I0*exp(-mod(t-t1,pi/377)/4e-3), 0);
vo = abs(io>1e-9).*509.*sin(377*t);
plot(t*1e3, vo); xlabel('t (ms)'); ylabel('v_o (V)'); grid on;
figure; plot(t*1e3, io); xlabel('t (ms)'); ylabel('i_o (A)'); grid on;
