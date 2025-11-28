/**
 * 通用动态粒子背景配置
 * 依赖: particles.min.js
 */

document.addEventListener('DOMContentLoaded', function() {
    // 检查页面上是否有 id="particles-js" 的容器，如果没有自动创建一个
    let container = document.getElementById('particles-js');

    if (!container) {
        container = document.createElement('div');
        container.id = 'particles-js';
        // 插入到 body 的最前面
        document.body.prepend(container);
    }

    // 启动粒子效果
    particlesJS("particles-js", {
        "particles": {
            "number": { "value": 80, "density": { "enable": true, "value_area": 800 } },
            "color": { "value": "#009688" }, // Layui 墨绿
            "shape": { "type": "circle", "stroke": { "width": 0, "color": "#000000" } },
            "opacity": { "value": 0.5, "random": false, "anim": { "enable": false } },
            "size": { "value": 3, "random": true, "anim": { "enable": false } },
            "line_linked": { "enable": true, "distance": 150, "color": "#009688", "opacity": 0.4, "width": 1 },
            "move": { "enable": true, "speed": 2, "direction": "none", "random": false, "straight": false, "out_mode": "out", "bounce": false, "attract": { "enable": false, "rotateX": 600, "rotateY": 1200 } }
        },
        "interactivity": {
            "detect_on": "canvas",
            "events": {
                "onhover": { "enable": true, "mode": "grab" },
                "onclick": { "enable": true, "mode": "push" },
                "resize": true
            },
            "modes": {
                "grab": { "distance": 140, "line_linked": { "opacity": 1 } },
                "push": { "particles_nb": 4 }
            }
        },
        "retina_detect": true
    });
});

