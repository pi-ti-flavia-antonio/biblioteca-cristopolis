// Foto do usuário: mostra uma prévia e reduz a imagem antes de enviar, para ficar leve no banco.
(function () {
    var campo = document.getElementById("foto");
    var previa = document.getElementById("foto-previa");
    if (!campo || !previa) { return; }

    var LADO_MAXIMO = 480;

    function mostrar(arquivo) {
        previa.src = URL.createObjectURL(arquivo);
        previa.hidden = false;
    }

    function reduzir(arquivo) {
        var url = URL.createObjectURL(arquivo);
        var imagem = new Image();
        imagem.onload = function () {
            var escala = Math.min(1, LADO_MAXIMO / Math.max(imagem.width, imagem.height));
            var tela = document.createElement("canvas");
            tela.width = Math.round(imagem.width * escala);
            tela.height = Math.round(imagem.height * escala);
            tela.getContext("2d").drawImage(imagem, 0, 0, tela.width, tela.height);
            URL.revokeObjectURL(url);
            tela.toBlob(function (blob) {
                if (!blob || blob.size >= arquivo.size) { return; }
                try {
                    var novo = new File([blob], "foto.jpg", { type: "image/jpeg" });
                    var lista = new DataTransfer();
                    lista.items.add(novo);
                    campo.files = lista.files;
                    mostrar(novo);
                } catch (erro) { /* mantém a foto original */ }
            }, "image/jpeg", 0.85);
        };
        imagem.onerror = function () { URL.revokeObjectURL(url); };
        imagem.src = url;
    }

    campo.addEventListener("change", function () {
        var arquivo = campo.files && campo.files[0];
        if (!arquivo || arquivo.type.indexOf("image/") !== 0) { return; }
        mostrar(arquivo);
        reduzir(arquivo);
    });
})();
