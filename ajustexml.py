import io
import re
import zipfile
import streamlit as st


def formatar_data(data):
    return f"{data[:4]}-{data[4:6]}-{data[6:]}"


def processar_conteudo_xml(conteudo: str) -> str:
    # enviPSCF -> enviPSCF versao="1.00"
    # Trata tanto <enviPSCF> simples quanto com possíveis espaços extras
    conteudo = re.sub(r"<enviPSCF\s*>", '<enviPSCF versao="1.00">', conteudo)

    # cEAN
    conteudo = re.sub(r"<cEAN\s*/>", "<cEAN>0</cEAN>", conteudo)

    # cEANTrib
    conteudo = re.sub(r"<cEANTrib\s*/>", "<cEANTrib>0</cEANTrib>", conteudo)

    # IEST
    def ajustar_iest(match):
        valor = match.group(1)
        valor = re.sub(r"\D", "", valor)
        return f"<IEST>{valor}</IEST>"

    conteudo = re.sub(r"<IEST>(.*?)</IEST>", ajustar_iest, conteudo)

    # INIC_TAB
    conteudo = re.sub(
        r"<INIC_TAB>(\d{8})</INIC_TAB>",
        lambda x: f"<INIC_TAB>{formatar_data(x.group(1))}</INIC_TAB>",
        conteudo,
    )

    # INIC_TAB_ANTERIOR
    conteudo = re.sub(
        r"<INIC_TAB_ANTERIOR>(\d{8})</INIC_TAB_ANTERIOR>",
        lambda x: f"<INIC_TAB_ANTERIOR>{formatar_data(x.group(1))}</INIC_TAB_ANTERIOR>",
        conteudo,
    )

    return conteudo


st.set_page_config(page_title="Processador de XMLs", layout="centered")

st.title("Corretor de Arquivos XML")
st.write("Faça o upload de um ou mais arquivos XML para processá-los em lote.")

arquivos_upload = st.file_uploader(
    "Selecione os arquivos XML",
    type=["xml"],
    accept_multiple_files=True,
)

if arquivos_upload:
    if st.button("Processar Arquivos", type="primary"):
        buffer_zip = io.BytesIO()
        sucessos = 0
        erros = []

        with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for arq in arquivos_upload:
                try:
                    raw_bytes = arq.read()

                    # Identifica encoding declarado no cabeçalho <?xml ... ?>
                    match_enc = re.search(
                        rb'<\?xml[^>]*encoding=["\']([^"\']+)["\']',
                        raw_bytes,
                        re.IGNORECASE,
                    )
                    encoding_declarado = (
                        match_enc.group(1).decode("ascii").lower()
                        if match_enc
                        else None
                    )

                    # Decodificação inteligente de caracteres
                    conteudo_original = None
                    encodings_para_tentar = [
                        encoding_declarado,
                        "iso-8859-1",
                        "windows-1252",
                        "utf-8",
                    ]
                    encodings_para_tentar = [
                        e for e in encodings_para_tentar if e
                    ]

                    for enc in encodings_para_tentar:
                        try:
                            conteudo_original = raw_bytes.decode(enc)
                            break
                        except (UnicodeDecodeError, LookupError):
                            continue

                    if conteudo_original is None:
                        conteudo_original = raw_bytes.decode(
                            "latin1", errors="replace"
                        )

                    # Correção de mojibake (caso acentos como Ç venham corrompidos como Ã‡)
                    try:
                        if "Ã" in conteudo_original or "Â" in conteudo_original:
                            conteudo_original = conteudo_original.encode(
                                "iso-8859-1"
                            ).decode("utf-8")
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        pass

                    # Aplica todas as substituições
                    conteudo_ajustado = processar_conteudo_xml(conteudo_original)

                    # Normaliza o cabeçalho para UTF-8
                    conteudo_ajustado = re.sub(
                        r'(<\?xml[^>]*encoding=["\'])[^"\']+(["\'])',
                        r"\g<1>utf-8\2",
                        conteudo_ajustado,
                        flags=re.IGNORECASE,
                    )

                    # Salva no ZIP codificado em UTF-8
                    zip_file.writestr(
                        arq.name, conteudo_ajustado.encode("utf-8")
                    )
                    sucessos += 1
                except Exception as e:
                    erros.append(f"{arq.name}: {str(e)}")

        buffer_zip.seek(0)

        if erros:
            for erro in erros:
                st.error(f"Erro ao processar: {erro}")

        st.success(
            f"{sucessos} de {len(arquivos_upload)} arquivo(s) processado(s) com sucesso!"
        )

        st.download_button(
            label="Baixar XMLs Processados (.ZIP)",
            data=buffer_zip,
            file_name="xmls_processados.zip",
            mime="application/zip",
        )
