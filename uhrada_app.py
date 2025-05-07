import streamlit as st
import re

# --- Data Parsing Logic ---

def parse_drug_block(drug_block_content):
    """
    Parses indications within a single drug's content block.
    drug_block_content typically starts with "### Indikace a podmínky úhrady".
    """
    drug_indications = []
    # Search for the specific H3 header for indications
    indication_header_match = re.search(r'### Indikace a podmínky úhrady\n', drug_block_content)
    
    if indication_header_match:
        content_after_header = drug_block_content[indication_header_match.end():]
    else:
        # If the H3 header is missing, we might assume the content directly contains indications.
        # Or, this could indicate a formatting variation. For now, we'll process the whole block.
        content_after_header = drug_block_content

    # Split by numbered indications: "1. **Some Cancer Type**:"
    # re.split with a capturing group (the parentheses around the pattern) keeps the delimiter.
    indications_raw = re.split(r'\n(\d+\.\s+\*\*(?:.+?)\*\*:)', content_after_header)
    
    # The first element of indications_raw is any text before the first numbered indication.
    # We start iterating from the first captured title.
    j = 1 # Index for the title
    while j < len(indications_raw):
        indication_title_line = indications_raw[j].strip()
        # Details for this indication are in the next element of the split list
        indication_details = indications_raw[j+1].strip() if (j+1) < len(indications_raw) else ""
        
        # Extract the clean indication category name from the bolded part of the title
        match = re.match(r'\d+\.\s+\*\*(.+?)\*\*:', indication_title_line)
        if match:
            clean_indication_name = match.group(1).strip() # .strip() to remove potential trailing spaces
            drug_indications.append({
                "full_title": indication_title_line, # e.g., "1. **Nemalobuněčný karcinom plic (NSCLC)**:"
                "indication_category": clean_indication_name, # e.g., "Nemalobuněčný karcinom plic (NSCLC)"
                "details": indication_details
            })
        j += 2 # Move to the next title-details pair (title is at j, details at j+1)
    return drug_indications

def parse_therapy_section(section_content_after_h1):
    """
    Parses a major therapy section (e.g., the content for "Imunoterapie"
    that comes AFTER its main H1 title).
    """
    general_conditions = ""
    drugs_in_section = {}

    # 1. Separate introductory paragraph from the rest.
    # The intro (like "Níže je přehled...") is usually before the first "---".
    # Content for General Conditions (GC) and drugs typically follows this first "---".
    parts_by_first_hr = section_content_after_h1.split("\n---\n", 1)
    content_for_gc_and_drugs = parts_by_first_hr[-1] # Takes content after first "---", or all content if no "---"

    # 2. Extract General Conditions.
    # GC block is "## Obecné podmínky pro úhradu..." and ends before the next "---" or the next "## DrugName".
    # Regex looks for GC header and captures content until next "---" or next H2 (drug) or end of block.
    gc_match = re.search(
        r"^(## Obecné podmínky pro úhradu.*?)(?:\n---\n|\n## \w|$)", 
        content_for_gc_and_drugs, 
        re.DOTALL | re.MULTILINE
    )
    # Assume all content is for drugs if GC block is not found by the specific pattern.
    drug_content_full = content_for_gc_and_drugs 

    if gc_match:
        general_conditions_text_block = gc_match.group(1)
        # Extract text that follows "## Obecné podmínky pro úhradu"
        general_conditions = general_conditions_text_block.split("## Obecné podmínky pro úhradu", 1)[1].strip()
        
        # Drug content is what remains after the GC block.
        end_of_gc_block = gc_match.end(0) # Position after the entire matched GC block.
        remaining_content_after_gc = content_for_gc_and_drugs[end_of_gc_block:].strip()
        
        # If this remaining content starts with "---" (separator), remove it.
        if remaining_content_after_gc.startswith("---\n"):
            drug_content_full = remaining_content_after_gc[len("---\n"):].strip()
        elif remaining_content_after_gc.startswith("---"): # Handles "---" without trailing newline
             drug_content_full = remaining_content_after_gc[len("---"):].strip()
        else:
            # No "---" immediately after GC block; drug definitions might start directly, or GC was the last H2.
            drug_content_full = remaining_content_after_gc
    # else: No "## Obecné podmínky pro úhradu" found as expected. 
    # drug_content_full remains as content_for_gc_and_drugs, which might be all drug definitions.

    # 3. Parse Drugs from drug_content_full.
    # Drug sections are "## Drug Name (Trade Name)\n### Indikace..."
    # Split `drug_content_full` by `\n## ` (using a lookahead `\n(?=##\s)` to keep `## ` part of the next string).
    # This ensures each "entry" starts with "## Drug Name...".
    drug_entries = re.split(r'\n(?=##\s)', drug_content_full) 

    for entry in drug_entries:
        entry = entry.strip()
        if not entry.startswith("## "): # Ensure it's a drug/poznámky section
            continue 

        # Each entry is "## DrugName (TradeName)\n### Indikace...\n..."
        # Extract the H2 drug header line and the content specific to that drug.
        first_line_end_index = entry.find('\n')
        if first_line_end_index == -1: # H2 header is the last line in this entry.
            h2_drug_header_line = entry[3:].strip() # Remove "## " from the start.
            drug_specific_content = ""
        else:
            h2_drug_header_line = entry[3:first_line_end_index].strip() # H2 line content.
            drug_specific_content = entry[first_line_end_index:].strip() # Content after H2 line.

        # Clean drug name: remove trade name in parentheses (e.g., "Pembrolizumab (Keytruda)" -> "Pembrolizumab").
        drug_name = re.sub(r'\s*\(.*?\)$', '', h2_drug_header_line).strip()

        if not drug_name: # Skip if drug name parsing failed.
            continue
        
        # Explicitly skip "Poznámky" sections if they are formatted with H2.
        if drug_name.lower() == "poznámky": 
            continue

        drugs_in_section[drug_name] = parse_drug_block(drug_specific_content)
        
    return general_conditions, drugs_in_section

def parse_complete_markdown(markdown_text):
    """
    Parses the entire markdown file, which can contain multiple main therapy type
    sections (e.g., Immunotherapy, Targeted Therapy). Each starts with a H1 heading.
    """
    parsed_data = {}
    
    # Split the document by major H1 headings like "# Podmínky úhrady XYZ..."
    # The regex `(?=^#\sPodmínky úhrady.*?$)` uses a positive lookahead to split
    # *before* each line that starts with "# Podmínky úhrady", keeping the H1 line as part of the section.
    sections = re.split(r'(?=^#\sPodmínky úhrady.*?$)', markdown_text, flags=re.MULTILINE)
    
    for section_block in sections:
        section_block = section_block.strip()
        if not section_block: # Skip empty parts that can result from the split.
            continue

        # Verify this block starts with the expected H1 format.
        h1_match = re.match(r'^#\s(Podmínky úhrady\s.*?)(?:\s*\(.*?\))?(?:.*?)$', section_block, re.IGNORECASE)
        
        if h1_match:
            full_h1_title = h1_match.group(1).strip() # e.g., "Podmínky úhrady imunoterapie v ČR"
            
            # Determine a shorter, user-friendly key for this therapy type.
            therapy_type_key = "Neznámý typ" # Default
            if "imunoterapie" in full_h1_title.lower():
                therapy_type_key = "Imunoterapie"
            elif "cílené léčby" in full_h1_title.lower() or "cílené terapie" in full_h1_title.lower():
                therapy_type_key = "Cílená léčba"
            else: # Fallback: clean up the H1 title for a key.
                therapy_type_key = full_h1_title.replace("Podmínky úhrady ", "").replace(" v ČR", "").strip()

            # Content for this therapy type is everything in section_block AFTER its H1 heading line.
            # h1_match.end(0) gives the index of the end of the entire matched H1 line.
            content_after_h1 = section_block[h1_match.end(0):].strip()
            
            general_conditions, drugs = parse_therapy_section(content_after_h1)
            
            # Add to parsed_data only if drugs were actually found for this therapy type.
            if drugs: 
                parsed_data[therapy_type_key] = {
                    "original_title": full_h1_title, # Store the full H1 for display
                    "general_conditions": general_conditions,
                    "drugs": drugs
                }
    return parsed_data

def get_all_indication_categories(parsed_data_dict):
    """Extracts all unique indication categories (cancer types) from parsed data."""
    categories = set()
    for therapy_type_data in parsed_data_dict.values(): # Iterate through each therapy type's data
        for drug_indications_list in therapy_type_data["drugs"].values(): # Iterate through drugs in that type
            for ind_data in drug_indications_list: # Iterate through indications of a drug
                categories.add(ind_data["indication_category"])
    return ["Všechny indikace"] + sorted(list(categories))

def get_all_drug_names_for_display(parsed_data_dict, selected_therapy_key="Všechny terapie"):
    """Gets drug names, optionally filtered by selected therapy type."""
    drug_names = set()
    if selected_therapy_key == "Všechny terapie":
        for therapy_type_data in parsed_data_dict.values():
            drug_names.update(therapy_type_data["drugs"].keys())
    elif selected_therapy_key in parsed_data_dict:
        drug_names.update(parsed_data_dict[selected_therapy_key]["drugs"].keys())
    return ["Všechny léky"] + sorted(list(drug_names))

# --- Streamlit App UI ---
st.set_page_config(layout="wide", page_title="Přehled úhrad léčiv")

st.title("⚕️ Přehled podmínek úhrady léčiv v ČR")
st.caption("Interaktivní přehled dle dokumentu SÚKL (zjednodušeno)")

# Load and parse the markdown file
try:
    with open("uhrada.markdown", "r", encoding="utf-8") as f:
        markdown_content = f.read()
except FileNotFoundError:
    st.error("Soubor 'uhrada.markdown' nebyl nalezen. Ujistěte se, že je ve stejném adresáři jako tento skript.")
    st.stop()

parsed_data = parse_complete_markdown(markdown_content)

if not parsed_data:
    st.warning("Nepodařilo se zpracovat data z Markdown souboru. Zkontrolujte formát souboru, zejména H1 nadpisy pro jednotlivé typy terapií (např. '# Podmínky úhrady imunoterapie...').")
    st.stop()

st.sidebar.header("Filtry")

# Filter for Therapy Type
therapy_types_available = ["Všechny terapie"] + sorted(list(parsed_data.keys()))
selected_therapy_type = st.sidebar.selectbox("Vyberte typ terapie:", therapy_types_available)

# Filter for Drug (dynamically populated based on selected therapy type)
drugs_for_selectbox = get_all_drug_names_for_display(parsed_data, selected_therapy_type)
selected_drug = st.sidebar.selectbox("Vyberte lék:", drugs_for_selectbox)

# Filter for Indication Category
all_indication_categories = get_all_indication_categories(parsed_data)
selected_indication_category = st.sidebar.selectbox("Vyberte typ diagnózy (indikace):", all_indication_categories)

st.markdown("---") # Visual separator in the main area

# Display General Conditions based on selected therapy type
if selected_therapy_type == "Všechny terapie":
    # Show general conditions for all available therapy types
    for therapy_key, data in parsed_data.items():
        if data["general_conditions"]: # Check if GC content exists
            with st.expander(f"📋 Obecné podmínky pro úhradu – {therapy_key} ({data['original_title']})", expanded=False):
                st.markdown(data["general_conditions"])
elif selected_therapy_type in parsed_data:
    # Show GC for the specifically selected therapy type
    data = parsed_data[selected_therapy_type]
    if data["general_conditions"]:
        with st.expander(f"📋 Obecné podmínky pro úhradu – {selected_therapy_type} ({data['original_title']})", expanded=True):
            st.markdown(data["general_conditions"])
else:
    # This case should ideally not be hit if selected_therapy_type is always from available_types
    st.info("Obecné podmínky pro vybraný typ terapie nebyly nalezeny nebo extrahovány.")


# --- Display Logic for Drugs and Indications ---
results_found = False
therapy_types_to_iterate = []

if selected_therapy_type == "Všechny terapie":
    therapy_types_to_iterate = parsed_data.keys() # Iterate all therapy types
elif selected_therapy_type in parsed_data:
    therapy_types_to_iterate = [selected_therapy_type] # Iterate only the selected one

for therapy_key in therapy_types_to_iterate:
    current_therapy_data = parsed_data[therapy_key]
    drugs_in_current_therapy = current_therapy_data["drugs"]
    
    drugs_to_display_for_this_therapy = []
    if selected_drug == "Všechny léky":
        drugs_to_display_for_this_therapy = sorted(drugs_in_current_therapy.keys())
    elif selected_drug in drugs_in_current_therapy: # Drug is selected and belongs to this therapy type
        drugs_to_display_for_this_therapy = [selected_drug]
    # If selected_drug is specific but not in drugs_in_current_therapy, this list remains empty,
    # so this therapy_key block will be skipped for drug display, which is correct.

    if not drugs_to_display_for_this_therapy: # No drugs match the filter for this therapy type
        continue

    # Determine if a header for the therapy type itself should be printed.
    # This is useful when "Všechny terapie" is selected and we are about to show drugs from one of them.
    # Only print if more than one therapy type exists in the data to avoid redundant headers for single-type views.
    needs_therapy_type_header = (selected_therapy_type == "Všechny terapie" and 
                                 len(parsed_data) > 1 and
                                 any(drug_name in drugs_in_current_therapy for drug_name in drugs_to_display_for_this_therapy))
    
    first_drug_output_for_this_therapy = True # Flag to print therapy header only once

    for drug_name_iter in drugs_to_display_for_this_therapy:
        indications_for_drug = drugs_in_current_therapy.get(drug_name_iter, [])
        
        # Filter indications by selected category
        filtered_indications = []
        if selected_indication_category == "Všechny indikace":
            filtered_indications = indications_for_drug
        else:
            for ind in indications_for_drug:
                if ind["indication_category"] == selected_indication_category:
                    filtered_indications.append(ind)
        
        if filtered_indications: # If there are indications to show for this drug after filtering
            results_found = True
            
            # Print the therapy type header if needed and not already printed for this type
            if needs_therapy_type_header and first_drug_output_for_this_therapy:
                st.header(f"🧬 {therapy_key} – {current_therapy_data['original_title']}")
                first_drug_output_for_this_therapy = False # Don't print again for this therapy type

            st.subheader(f"💊 {drug_name_iter}")
            for ind_data in filtered_indications:
                st.markdown(f"**{ind_data['full_title']}**")
                # Format details: convert simple list hyphens to markdown bullets
                detail_lines = ind_data['details'].split('\n')
                formatted_details = [re.sub(r'^\s*-\s+', '* ', line) for line in detail_lines]
                st.markdown("\n".join(formatted_details))
                st.markdown("---") # Separator between indications of the same drug, or after last indication.

if not results_found:
    st.info("Nebyly nalezeny žádné výsledky pro zadané filtry.")

st.sidebar.markdown("---")
st.sidebar.info("Aplikace vytvořená pro rychlý přehled podmínek úhrady léčiv.")