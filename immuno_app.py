import streamlit as st
import re

# --- Data Parsing Logic ---

def parse_markdown(markdown_text):
    """
    Parses the provided markdown text into a structured format.
    """
    general_conditions = ""
    drug_specific_conditions = {}
    current_drug = None
    
    sections = markdown_text.split("\n---\n") # Split by the horizontal rules

    # First section is usually the title, second is General Conditions
    if len(sections) > 1:
        # Find General Conditions
        general_conditions_header = "## Obecné podmínky pro úhradu"
        for i, sec in enumerate(sections):
            if general_conditions_header in sec:
                general_conditions = sec.split(general_conditions_header, 1)[1].strip()
                # Remove the general conditions section from further processing
                sections = sections[:i] + sections[i+1:]
                break
    
    # Process remaining sections for drugs
    drug_content_full = "\n---\n".join(sections) # Re-join if there were other "---"
    drug_blocks = re.split(r'\n## (.*?)\n', drug_content_full)
    
    # drug_blocks will be like ['', 'Pembrolizumab', 'content for pembro...', '', 'Nivolumab', 'content for nivo...', ...]
    # So we iterate in steps of 2, starting from index 1
    
    i = 1
    while i < len(drug_blocks):
        drug_name = drug_blocks[i].strip()
        if not drug_name or drug_name.startswith("#"): # Skip empty or title lines
            i += 1
            continue
        
        content = drug_blocks[i+1].strip() if (i+1) < len(drug_blocks) else ""
        
        drug_specific_conditions[drug_name] = []
        
        # Find "Indikace a podmínky úhrady" section if it exists
        indication_header_match = re.search(r'### Indikace a podmínky úhrady\n', content)
        if indication_header_match:
            content_after_header = content[indication_header_match.end():]
        else:
            content_after_header = content # Assume content starts directly with indications

        # Split by numbered indications: "1. **Some Cancer**:"
        indications_raw = re.split(r'\n(\d+\.\s+\*\*(?:.+?)\*\*:)', content_after_header)
        
        # indications_raw will be like ['', '1. **NSCLC**:', 'details for NSCLC...', '2. **Melanom**:', 'details for Melanom...']
        j = 1
        while j < len(indications_raw):
            indication_title_line = indications_raw[j].strip()
            indication_details = indications_raw[j+1].strip() if (j+1) < len(indications_raw) else ""
            
            # Extract clean indication name from title line
            match = re.match(r'\d+\.\s+\*\*(.+?)\*\*:', indication_title_line)
            if match:
                clean_indication_name = match.group(1)
                drug_specific_conditions[drug_name].append({
                    "full_title": indication_title_line, # e.g., "1. **Nemalobuněčný karcinom plic (NSCLC)**:"
                    "indication_category": clean_indication_name, # e.g., "Nemalobuněčný karcinom plic (NSCLC)"
                    "details": indication_details
                })
            j += 2
            
        i += 2
        
    return general_conditions, drug_specific_conditions

def get_all_indication_categories(drug_data):
    """Extracts all unique indication categories (cancer types)."""
    categories = set()
    for drug, indications in drug_data.items():
        for ind in indications:
            categories.add(ind["indication_category"])
    return sorted(list(categories))

# --- Streamlit App UI ---

st.set_page_config(layout="wide", page_title="Imunoterapie v ČR")

st.title("🔍 Podmínky úhrady imunoterapie v ČR")
st.caption("Interaktivní přehled dle dokumentu SÚKL (zjednodušeno)")

# Load and parse the markdown file
try:
    with open("Podmínky úhrady imunoterapie.markdown", "r", encoding="utf-8") as f:
        markdown_content = f.read()
except FileNotFoundError:
    st.error("Soubor 'Podmínky úhrady imunoterapie.markdown' nebyl nalezen. Ujistěte se, že je ve stejném adresáři jako tento skript.")
    st.stop()

general_conditions, drug_data = parse_markdown(markdown_content)

if not drug_data:
    st.warning("Nepodařilo se zpracovat data o lécích. Zkontrolujte formát Markdown souboru.")
    st.stop()

# Display General Conditions
if general_conditions:
    with st.expander("📋 Obecné podmínky pro úhradu (platí pro všechny léky, pokud není uvedeno jinak)", expanded=False):
        st.markdown(general_conditions)
else:
    st.info("Obecné podmínky nebyly v souboru nalezeny nebo extrahovány.")

st.sidebar.header("Filtry")

all_drugs = ["Všechny léky"] + sorted(list(drug_data.keys()))
selected_drug = st.sidebar.selectbox("Vyberte lék:", all_drugs)

all_indications = ["Všechny indikace"] + get_all_indication_categories(drug_data)
selected_indication_category = st.sidebar.selectbox("Vyberte typ diagnózy (indikace):", all_indications)

st.markdown("---") # Visual separator

# --- Display Logic ---
results_found = False

drugs_to_display = []
if selected_drug == "Všechny léky":
    drugs_to_display = sorted(drug_data.keys())
else:
    drugs_to_display = [selected_drug]

for drug_name in drugs_to_display:
    if drug_name not in drug_data:
        continue

    indications_for_drug = drug_data[drug_name]
    
    # Filter indications for this drug based on selected_indication_category
    filtered_indications = []
    if selected_indication_category == "Všechny indikace":
        filtered_indications = indications_for_drug
    else:
        for ind in indications_for_drug:
            if ind["indication_category"] == selected_indication_category:
                filtered_indications.append(ind)
    
    if filtered_indications:
        results_found = True
        st.subheader(f"💊 {drug_name}")
        for ind_data in filtered_indications:
            # Reconstruct the original numbered title for display
            st.markdown(f"**{ind_data['full_title']}**")
            # Split details by sub-bullets for better formatting if needed, or display as is
            # For simplicity, displaying details as a block. Could be refined.
            
            # Make sure sub-bullets are also markdown formatted correctly
            # Replace leading spaces before hyphens with markdown list items
            detail_lines = ind_data['details'].split('\n')
            formatted_details = []
            for line in detail_lines:
                # Convert "- " to "* " or "- " for markdown lists
                line = re.sub(r'^\s*-\s+', '* ', line) # Handles indented list items too
                formatted_details.append(line)

            st.markdown("\n".join(formatted_details))
            st.markdown("---") # Separator between indications for the same drug

if not results_found:
    st.info("Nebyly nalezeny žádné výsledky pro zadané filtry.")

st.sidebar.markdown("---")
st.sidebar.info("Aplikace vytvořená pro rychlý přehled podmínek úhrady imunoterapie.")