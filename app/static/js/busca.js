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

    function iniciar(raiz) {
        var url = raiz.dataset.url;
        var nome = raiz.dataset.nome;
        var oculto = raiz.querySelector("input[type=hidden]");
        var caixa = raiz.querySelector("[data-caixa]");
        var campo = caixa.querySelector("input");
        var lista = raiz.querySelector("[data-lista]");
        var escolhido = raiz.querySelector("[data-escolhido]");
        var textoEscolhido = escolhido.querySelector("[data-texto]");
        var itens = [];
        var ativo = -1;
        var pedido = 0;
        var temporizador = null;

        function abrir(aberta) {
            lista.style.display = aberta ? "block" : "none";
            campo.setAttribute("aria-expanded", aberta ? "true" : "false");
            if (!aberta) campo.removeAttribute("aria-activedescendant");
        }

        function proximoDisponivel(inicio, passo) {
            for (var i = inicio; i >= 0 && i < itens.length; i += passo) {
                if (itens[i].disponiveis !== 0) return i;
            }
            return -1;
        }

        function marcar() {
            var opcoes = lista.querySelectorAll("li[role=option]");
            for (var i = 0; i < opcoes.length; i++) {
                opcoes[i].setAttribute("aria-selected", i === ativo ? "true" : "false");
            }
            if (ativo > -1) campo.setAttribute("aria-activedescendant", opcoes[ativo].id);
        }

        function desenhar(termo) {
            if (!itens.length) {
                lista.innerHTML = '<li class="sg__vazio">Nenhum ' + nome + ' encontrado para "' + escapar(termo.trim()) + '".</li>';
                ativo = -1;
            } else {
                lista.innerHTML = itens.map(function (item, i) {
                    var esgotado = item.disponiveis === 0;
                    var selo = "";
                    if (typeof item.disponiveis === "number") {
                        selo = esgotado
                            ? '<span class="badge badge--overdue">Sem exemplar</span>'
                            : '<span class="badge">' + item.disponiveis + (item.disponiveis === 1 ? " disponível" : " disponíveis") + "</span>";
                    }
                    var sub = item.subtitulo ? '<span class="sg__sub">' + destacar(item.subtitulo, termo) + "</span>" : "";
                    return '<li role="option" id="' + lista.id + "-" + i + '" data-i="' + i + '"' +
                        (esgotado ? ' class="sg__esgotado" aria-disabled="true"' : "") + ' aria-selected="false">' +
                        "<span>" + destacar(item.titulo, termo) + sub + "</span>" + selo + "</li>";
                }).join("");
                ativo = proximoDisponivel(0, 1);
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
            fetch(url + "?q=" + encodeURIComponent(termo.trim()), { headers: { Accept: "application/json" } })
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
            if (!item || item.disponiveis === 0) return;
            oculto.value = item.id;
            textoEscolhido.textContent = nome === "livro"
                ? item.titulo + ", de " + item.subtitulo
                : item.titulo + (item.subtitulo ? " (" + item.subtitulo.replace(/^CPF /, "") + ")" : "");
            caixa.hidden = true;
            escolhido.hidden = false;
            abrir(false);
            var erro = raiz.querySelector(".field__error");
            if (erro) erro.remove();
        }

        campo.addEventListener("input", function () {
            clearTimeout(temporizador);
            temporizador = setTimeout(buscar, ESPERA_MS);
        });

        campo.addEventListener("focus", function () {
            if (campo.value.trim()) buscar();
        });

        campo.addEventListener("keydown", function (evento) {
            if (evento.key === "Enter") {
                evento.preventDefault();
                if (lista.style.display === "block" && ativo > -1) escolher(ativo);
                return;
            }
            if (lista.style.display !== "block") return;
            if (evento.key === "ArrowDown") {
                evento.preventDefault();
                var proximo = proximoDisponivel(ativo + 1, 1);
                if (proximo > -1) { ativo = proximo; marcar(); }
            } else if (evento.key === "ArrowUp") {
                evento.preventDefault();
                var anterior = proximoDisponivel(ativo - 1, -1);
                if (anterior > -1) { ativo = anterior; marcar(); }
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
            if (opcao && itens[Number(opcao.dataset.i)].disponiveis !== 0) {
                ativo = Number(opcao.dataset.i);
                marcar();
            }
        });

        document.addEventListener("click", function (evento) {
            if (!caixa.contains(evento.target)) abrir(false);
        });

        escolhido.querySelector("[data-trocar]").addEventListener("click", function () {
            oculto.value = "";
            escolhido.hidden = true;
            caixa.hidden = false;
            campo.value = "";
            campo.focus();
        });
    }

    var campos = document.querySelectorAll("[data-busca]");
    for (var i = 0; i < campos.length; i++) iniciar(campos[i]);
})();
