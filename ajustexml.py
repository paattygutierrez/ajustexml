import io
import re
import zipfile
import streamlit as st


def formatar_data(data):
    return f"{data[:4]}-{data[4:6]}-{data[6:]}"


def processar_conteudo_xml(conteudo: str) -> str:
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


# Interface Streamlit
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
                    conteudo_original = arq.read().decode("utf-8")
                    conteudo_ajustado = processar_conteudo_xml(conteudo_original)
                    
                    # Adiciona o arquivo processado ao ZIP
                    zip_file.writestr(arq.name, conteudo_ajustado)
                    sucessos += 1
                except Exception as e:
                    erros.append(f"{arq.name}: {str(e)}")

        buffer_zip.seek(0)

        if erros:
            for erro in erros:
                st.error(f"Erro ao processar: {erro}")

        st.success(f"{sucessos} de {len(arquivos_upload)} arquivo(s) processado(s) com sucesso!")

        st.download_button(
            label="Baixar XMLs Processados (.ZIP)",
            data=buffer_zip,
            file_name="xmls_processados.zip",
            mime="application/zip",
        )