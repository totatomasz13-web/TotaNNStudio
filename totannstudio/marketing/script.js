document.documentElement.classList.remove('no-js');
document.documentElement.classList.add('js');

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });

document.querySelectorAll('.reveal').forEach((element) => revealObserver.observe(element));

const epoch = document.querySelector('.epoch-value');
let epochValue = 68;
setInterval(() => {
  if (document.hidden || !epoch) return;
  epochValue = epochValue >= 99 ? 68 : epochValue + 1;
  epoch.textContent = String(epochValue);
}, 2400);

const chartButtons = document.querySelectorAll('.chart-controls button');
chartButtons.forEach((button) => {
  button.addEventListener('click', () => {
    chartButtons.forEach((item) => item.classList.remove('active'));
    button.classList.add('active');
  });
});
