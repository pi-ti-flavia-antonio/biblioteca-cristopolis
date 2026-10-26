(function () {
    var ESPERA_MS = 150;

    function normalizar(texto) {
        return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    }

    function escapar(texto) {
        return String(texto).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function destacar(texto, termo) {
        var procurado = normalizar(termo.trim());
        var posicao = procurado ? normalizar(texto).indexOf(procurado) : -1;
        if (posicao < 0) return escapar(texto);
        var fim = posicao + procurado.length;
        return escapar(texto.slice(0, posicao)) + "<mark>" + escapar(texto.slice(posicao, fim)) + "</mark>" + escapar(texto.slice(fim));
    }

    function montarUrl(url, termo) {
        return url + (url.indexOf("?") > -1 ? "&" : "?") + "q=" + encodeURIComponent(termo.trim());
    }

    function sugestoes(cfg) {
        var campo = cfg.campo;
        var lista = cfg.lista;
        var itens = [];
        var ativo = -1;
        var pedido = 0;
        var temporizador = null;

        function desabilitado(item) {
            return cfg.desabilitado ? cfg.desabilitado(item) : false;
        }

        function abrir(aberta) {
            lista.style.display = aberta ? "block" : "none";
            campo.setAttribute("aria-expanded", aberta ? "true" : "false");
            if (!aberta) campo.removeAttribute("aria-activedescendant");
        }

        function proximoDisponivel(inicio, passo) {
            for (var i = inicio; i >= 0 && i < itens.length; i += passo) {
                if (!desabilitado(itens[i])) return i;
            }
            return -1;
        }

        function marcar() {
            var opcoes = lista.querySelectorAll("li[role=option]");
            for (var i = 0; i < opcoes.length; i++) {
                opcoes[i].setAttribute("aria-selected", i === ativo ? "true" : "false");
            }
            if (ativo > -1) campo.setAttribute("aria-activedescendant", opcoes[ativo].id);
            else campo.removeAttribute("aria-activedescendant");
        }

        function selo(item) {
            if (typeof item.disponiveis === "number") {
                return item.disponiveis === 0
                    ? '<span class="badge badge--overdue">Indisponível</span>'
                    : '<span class="badge">' + item.disponiveis + (item.disponiveis === 1 ? " disponível" : " disponíveis") + "</span>";
            }
            if (item.rotulo) return '<span class="badge badge--neutral">' + escapar(item.rotulo) + "</span>";
            return "";
        }

        function desenhar(termo) {
            if (!itens.length) {
                lista.innerHTML = '<li class="sg__vazio">Nenhum ' + cfg.nome + ' encontrado para "' + escapar(termo.trim()) + '".</li>';
                ativo = -1;
            } else {
                lista.innerHTML = itens.map(function (item, i) {
                    var bloqueado = desabilitado(item);
                    var sub = item.subtitulo ? '<span class="sg__sub">' + destacar(item.subtitulo, termo) + "</span>" : "";
                    return '<li role="option" id="' + lista.id + "-" + i + '" data-i="' + i + '"' +
                        (bloqueado ? ' class="sg__esgotado" aria-disabled="true"' : "") + ' aria-selected="false">' +
                        "<span>" + destacar(item.titulo, termo) + sub + "</span>" + selo(item) + "</li>";
                }).join("");
                ativo = cfg.marcarPrimeiro ? proximoDisponivel(0, 1) : -1;
            }
            abrir(true);
            marcar();
        }

        function buscar() {
            var termo = campo.value;
            if (!termo.trim()) {
                pedido++;
                abrir(false);
                return;
            }
            var este = ++pedido;
            fetch(montarUrl(cfg.url, termo), { headers: { Accept: "application/json" } })
                .then(function (resposta) { return resposta.json(); })
                .then(function (dados) {
                    if (este !== pedido) return;
                    itens = dados.itens;
                    desenhar(termo);
                })
                .catch(function () {
                    if (este !== pedido) return;
                    itens = [];
                    lista.innerHTML = '<li class="sg__vazio">Não foi possível buscar agora. Tente de novo.</li>';
                    abrir(true);
                });
        }

        function escolher(i) {
            var item = itens[i];
            if (!item || desabilitado(item)) return;
            abrir(false);
            cfg.aoEscolher(item);
        }

        campo.addEventListener("input", function () {
            clearTimeout(temporizador);
            temporizador = setTimeout(buscar, ESPERA_MS);
        });

        campo.addEventListener("focus", function () {
            if (campo.value.trim()) buscar();
        });

        campo.addEventListener("keydown", function (evento) {
            var aberta = lista.style.display === "block";
            if (evento.key === "Enter") {
                if (aberta && ativo > -1) {
                    evento.preventDefault();
                    escolher(ativo);
                } else if (cfg.bloquearEnter) {
                    evento.preventDefault();
                }
                return;
            }
            if (!aberta) return;
            if (evento.key === "ArrowDown") {
                evento.preventDefault();
                var proximo = proximoDisponivel(ativo + 1, 1);
                if (proximo > -1) { ativo = proximo; marcar(); }
            } else if (evento.key === "ArrowUp") {
                evento.preventDefault();
                var anterior = proximoDisponivel(ativo - 1, -1);
                if (anterior > -1) { ativo = anterior; marcar(); }
                else if (!cfg.marcarPrimeiro) { ativo = -1; marcar(); }
            } else if (evento.key === "Escape") {
                abrir(false);
            }
        });

        lista.addEventListener("mousedown", function (evento) {
            var opcao = evento.target.closest("li[role=option]");
            if (opcao) {
                evento.preventDefault();
                escolher(Number(opcao.dataset.i));
            }
        });

        lista.addEventListener("mousemove", function (evento) {
            var opcao = evento.target.closest("li[role=option]");
            if (opcao && !desabilitado(itens[Number(opcao.dataset.i)])) {
                ativo = Number(opcao.dataset.i);
                marcar();
            }
        });

        document.addEventListener("click", function (evento) {
            if (!cfg.caixa.contains(evento.target)) abrir(false);
        });
    }

    function iniciarEscolha(raiz) {
        var nome = raiz.dataset.nome;
        var reserva = raiz.hasAttribute("data-reserva");
        var oculto = raiz.querySelector("input[type=hidden]");
        var caixa = raiz.querySelector("[data-caixa]");
        var campo = caixa.querySelector("input");
        var escolhido = raiz.querySelector("[data-escolhido]");
        var textoEscolhido = escolhido.querySelector("[data-texto]");

        sugestoes({
            campo: campo,
            lista: raiz.querySelector("[data-lista]"),
            caixa: caixa,
            url: raiz.dataset.url,
            nome: nome,
            marcarPrimeiro: true,
            bloquearEnter: true,
            desabilitado: function (item) {
                if (typeof item.disponiveis !== "number") return false;
                return reserva ? item.disponiveis !== 0 : item.disponiveis === 0;
            },
            aoEscolher: function (item) {
                oculto.value = item.id;
                textoEscolhido.textContent = typeof item.disponiveis === "number"
                    ? item.titulo + ", de " + item.subtitulo
                    : item.titulo + (item.subtitulo ? " (" + item.subtitulo.replace(/^CPF /, "") + ")" : "");
                caixa.hidden = true;
                escolhido.hidden = false;
                var erro = raiz.querySelector(".field__error");
                if (erro) erro.remove();
            }
        });

        escolhido.querySelector("[data-trocar]").addEventListener("click", function () {
            oculto.value = "";
            escolhido.hidden = true;
            caixa.hidden = false;
            campo.value = "";
            campo.focus();
        });
    }

    function iniciarFiltro(raiz) {
        var caixa = raiz.querySelector(".sbox");
        var campo = caixa.querySelector("input");
        var formulario = campo.form;

        sugestoes({
            campo: campo,
            lista: raiz.querySelector("[data-lista]"),
            caixa: caixa,
            url: raiz.dataset.url,
            nome: raiz.dataset.nome,
            marcarPrimeiro: false,
            bloquearEnter: false,
            aoEscolher: function (item) {
                campo.value = item.titulo;
                formulario.submit();
            }
        });
    }

    var escolhas = document.querySelectorAll("[data-busca]");
    for (var i = 0; i < escolhas.length; i++) iniciarEscolha(escolhas[i]);

    var filtros = document.querySelectorAll("[data-busca-filtro]");
    for (var j = 0; j < filtros.length; j++) iniciarFiltro(filtros[j]);
})();
