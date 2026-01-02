/* ========================================
   MultiMax - Mobile Enhancements
   Melhorias e otimizações JavaScript para dispositivos móveis
   ======================================== */

(function() {
    'use strict';

    // Detectar se é dispositivo móvel
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

    if (!isMobile && !isTouch) return; // Sair se não for mobile

    // ===== PREVENÇÃO DE ZOOM DUPLO TOQUE =====
    let lastTouchEnd = 0;
    document.addEventListener('touchend', function(event) {
        const now = Date.now();
        if (now - lastTouchEnd <= 300) {
            event.preventDefault();
        }
        lastTouchEnd = now;
    }, false);

    // ===== MELHORAR SCROLL EM TABELAS =====
    const tables = document.querySelectorAll('.table-wrapper, .mm-table-wrapper, [class*="table-wrapper"]');
    tables.forEach(table => {
        let isScrolling = false;
        let startX = 0;
        let scrollLeft = 0;

        table.addEventListener('touchstart', (e) => {
            isScrolling = true;
            startX = e.touches[0].pageX - table.offsetLeft;
            scrollLeft = table.scrollLeft;
        });

        table.addEventListener('touchmove', (e) => {
            if (!isScrolling) return;
            e.preventDefault();
            const x = e.touches[0].pageX - table.offsetLeft;
            const walk = (x - startX) * 2;
            table.scrollLeft = scrollLeft - walk;
        });

        table.addEventListener('touchend', () => {
            isScrolling = false;
        });
    });

    // ===== FECHAR MODAIS COM SWIPE DOWN =====
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        let startY = 0;
        let currentY = 0;
        let isDragging = false;

        const modalContent = modal.querySelector('.modal-content, .modern-modal');
        if (!modalContent) return;

        modalContent.addEventListener('touchstart', (e) => {
            if (modalContent.scrollTop === 0) {
                isDragging = true;
                startY = e.touches[0].clientY;
            }
        });

        modalContent.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            currentY = e.touches[0].clientY;
            const diff = currentY - startY;

            if (diff > 0 && modalContent.scrollTop === 0) {
                modalContent.style.transform = `translateY(${Math.min(diff, 100)}px)`;
                modalContent.style.opacity = Math.max(0.7, 1 - diff / 200);
            }
        });

        modalContent.addEventListener('touchend', () => {
            if (currentY - startY > 100) {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            }
            modalContent.style.transform = '';
            modalContent.style.opacity = '';
            isDragging = false;
        });
    });

    // ===== MELHORAR NAVEGAÇÃO DO SIDEBAR =====
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (sidebar && overlay) {
        // Fechar sidebar ao tocar no overlay
        overlay.addEventListener('touchstart', () => {
            if (sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
                overlay.classList.remove('active');
            }
        });

        // Fechar sidebar ao deslizar para a esquerda
        let touchStartX = 0;
        let touchEndX = 0;

        sidebar.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
        });

        sidebar.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        });

        function handleSwipe() {
            if (touchEndX < touchStartX - 50 && sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
                overlay.classList.remove('active');
            }
        }
    }

    // ===== OTIMIZAR INPUTS PARA MOBILE =====
    const inputs = document.querySelectorAll('input[type="text"], input[type="number"], input[type="email"], textarea');
    inputs.forEach(input => {
        // Prevenir zoom no iOS
        if (input.style.fontSize === '' || parseInt(input.style.fontSize) < 16) {
            input.style.fontSize = '16px';
        }

        // Adicionar botão de limpar em inputs de texto
        if (input.type === 'text' || input.type === 'email') {
            input.addEventListener('input', function() {
                if (this.value && !this.parentElement.querySelector('.input-clear')) {
                    const clearBtn = document.createElement('button');
                    clearBtn.type = 'button';
                    clearBtn.className = 'input-clear';
                    clearBtn.innerHTML = '<i class="bi bi-x-circle"></i>';
                    clearBtn.style.cssText = 'position: absolute; right: 0.5rem; top: 50%; transform: translateY(-50%); background: none; border: none; color: var(--mm-text-muted); font-size: 1.25rem; padding: 0.25rem; cursor: pointer; z-index: 10;';
                    clearBtn.addEventListener('click', () => {
                        this.value = '';
                        this.focus();
                        clearBtn.remove();
                    });
                    if (this.parentElement.style.position !== 'relative') {
                        this.parentElement.style.position = 'relative';
                    }
                    this.parentElement.appendChild(clearBtn);
                } else if (!this.value) {
                    const clearBtn = this.parentElement.querySelector('.input-clear');
                    if (clearBtn) clearBtn.remove();
                }
            });
        }
    });

    // ===== MELHORAR SELECTS MOBILE =====
    const selects = document.querySelectorAll('select');
    selects.forEach(select => {
        // Adicionar indicador visual de seleção
        select.addEventListener('change', function() {
            if (this.value) {
                this.style.color = 'var(--mm-text-primary)';
            } else {
                this.style.color = 'var(--mm-text-muted)';
            }
        });
    });

    // ===== LAZY LOADING DE IMAGENS =====
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        observer.unobserve(img);
                    }
                }
            });
        });

        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }

    // ===== PREVENIR SCROLL HORIZONTAL ACIDENTAL =====
    let lastTouchX = 0;
    document.addEventListener('touchstart', (e) => {
        lastTouchX = e.touches[0].clientX;
    });

    document.addEventListener('touchmove', (e) => {
        const touchX = e.touches[0].clientX;
        const touchY = e.touches[0].clientY;
        const deltaX = Math.abs(touchX - lastTouchX);
        const deltaY = Math.abs(touchY - e.touches[0].clientY);

        // Se o movimento horizontal for maior que o vertical, permitir scroll horizontal
        if (deltaX > deltaY) {
            return;
        }

        // Prevenir scroll horizontal acidental na página principal
        const target = e.target;
        const scrollable = target.closest('.table-wrapper, .mm-table-wrapper, [class*="table-wrapper"], [style*="overflow"]');
        
        if (!scrollable && Math.abs(touchX - lastTouchX) > 10) {
            e.preventDefault();
        }
    });

    // ===== MELHORAR FEEDBACK TÁTIL =====
    const buttons = document.querySelectorAll('button, a.btn, .mm-btn, [role="button"]');
    buttons.forEach(button => {
        button.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.98)';
            this.style.transition = 'transform 0.1s';
        });

        button.addEventListener('touchend', function() {
            setTimeout(() => {
                this.style.transform = '';
            }, 100);
        });
    });

    // ===== OTIMIZAR PERFORMANCE =====
    // Debounce para eventos de scroll
    let scrollTimeout;
    window.addEventListener('scroll', () => {
        if (scrollTimeout) {
            cancelAnimationFrame(scrollTimeout);
        }
        scrollTimeout = requestAnimationFrame(() => {
            // Operações de scroll otimizadas
        });
    }, { passive: true });

    // ===== DETECTAR ORIENTAÇÃO =====
    window.addEventListener('orientationchange', () => {
        setTimeout(() => {
            window.scrollTo(0, 0);
            // Recalcular layouts se necessário
            if (typeof window.dispatchEvent === 'function') {
                window.dispatchEvent(new Event('resize'));
            }
        }, 100);
    });

    // ===== MELHORAR ACESSIBILIDADE TOUCH =====
    // Aumentar área de toque para elementos pequenos
    const smallButtons = document.querySelectorAll('.btn-sm, .mm-btn-sm, [class*="btn-sm"]');
    smallButtons.forEach(btn => {
        if (btn.offsetWidth < 44 || btn.offsetHeight < 44) {
            btn.style.minWidth = '44px';
            btn.style.minHeight = '44px';
            btn.style.padding = '0.625rem 1rem';
        }
    });

    // ===== PREVENIR SELEÇÃO ACIDENTAL DE TEXTO =====
    const noSelectElements = document.querySelectorAll('.btn, button, .mm-btn, .action-card, .kpi-card');
    noSelectElements.forEach(el => {
        el.style.userSelect = 'none';
        el.style.webkitUserSelect = 'none';
        el.style.webkitTouchCallout = 'none';
    });

    // ===== MELHORAR FORMULÁRIOS MOBILE =====
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        // Focar no primeiro campo ao abrir modal
        form.addEventListener('shown.bs.modal', function() {
            const firstInput = form.querySelector('input, select, textarea');
            if (firstInput && firstInput.type !== 'hidden') {
                setTimeout(() => firstInput.focus(), 300);
            }
        });

        // Submeter formulário com Enter em mobile
        form.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn && !submitBtn.disabled) {
                    e.preventDefault();
                    submitBtn.click();
                }
            }
        });
    });

    // ===== INDICADOR DE CARREGAMENTO TOUCH =====
    let touchStartTime = 0;
    document.addEventListener('touchstart', (e) => {
        touchStartTime = Date.now();
    });

    document.addEventListener('touchend', (e) => {
        const touchDuration = Date.now() - touchStartTime;
        if (touchDuration > 500) {
            // Long press - pode adicionar feedback visual
            const target = e.target;
            if (target.classList.contains('long-pressable')) {
                target.style.backgroundColor = 'rgba(0, 255, 136, 0.1)';
                setTimeout(() => {
                    target.style.backgroundColor = '';
                }, 200);
            }
        }
    });

    // ===== MELHORAR NAVEGAÇÃO POR TABS =====
    const tabButtons = document.querySelectorAll('.tab-btn, [role="tab"]');
    tabButtons.forEach(tab => {
        tab.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.95)';
        });

        tab.addEventListener('touchend', function() {
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });

    // ===== OTIMIZAR ANIMAÇÕES PARA MOBILE =====
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (prefersReducedMotion.matches) {
        document.documentElement.style.setProperty('--mm-transition', '0s');
    }

    // ===== PREVENIR MENU CONTEXTUAL EM LONG PRESS =====
    document.addEventListener('contextmenu', (e) => {
        if (isTouch) {
            e.preventDefault();
        }
    });

    // ===== MELHORAR FEEDBACK VISUAL EM TOUCH =====
    document.addEventListener('touchstart', (e) => {
        const target = e.target.closest('a, button, .mm-btn, [role="button"], .action-card, .kpi-card');
        if (target && !target.classList.contains('no-touch-feedback')) {
            target.style.opacity = '0.8';
        }
    }, { passive: true });

    document.addEventListener('touchend', (e) => {
        const target = e.target.closest('a, button, .mm-btn, [role="button"], .action-card, .kpi-card');
        if (target) {
            setTimeout(() => {
                target.style.opacity = '';
            }, 150);
        }
    }, { passive: true });

    // ===== CONSOLE LOG PARA DEBUG (apenas em desenvolvimento) =====
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.log('📱 MultiMax Mobile Enhancements carregado');
        console.log('Dispositivo:', isMobile ? 'Mobile' : 'Desktop');
        console.log('Touch:', isTouch ? 'Sim' : 'Não');
    }

})();

