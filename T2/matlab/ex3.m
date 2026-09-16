t = linspace(0, 1/60, 3000);
io = (t>=1.343e-3 & t<=9.70e-3).*(6.96*sin(377*t-0.513)+0.047*exp(-(t-1.343e-3)/1.5e-3));
vo = (io~=0).*240.*sin(377*t);
plot(t*1e3, vo); xlabel('t (ms)'); ylabel('v_o (V)'); grid on;
figure; plot(t*1e3, io); xlabel('t (ms)'); ylabel('i_o (A)'); grid on;
