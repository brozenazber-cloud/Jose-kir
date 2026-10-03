const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)e.target.style.opacity=1}),{threshold:.08});
document.querySelectorAll('.card,.about').forEach(x=>{x.style.opacity=0;x.style.transition='opacity .8s ease,transform .35s ease';io.observe(x)});
