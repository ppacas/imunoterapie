import streamlit as st
import re

# Predefined list of known immunotherapy drugs.
IMUNOTHERAPY_DRUGS_KEYWORDS = [
    "Pembrolizumab", "Nivolumab", "Ipilimumab", "Durvalumab", "Avelumab", "Dostarlimab"
]

def get_drug_type(drug_name_cleaned):
    if drug_name_cleaned in IMUNOTHERAPY_DRUGS_KEYWORDS:
        return "Imunoterapie"
    return "Cílená léčba"

def parse_indications_from_drug_content_h4(drug_specific_content):
    indications = []
    # Look for H4 "#### Indikace a podmínky úhrady"
    indication_header_match = re.search(r'#### Indikace a podmínky úhrady\n', drug_specific_content)
    
    content_after_indication_header = drug_specific_content
    if indication_header_match:
        content_after_indication_header = drug_specific_content[indication_header_match.end():]

    indications_raw = re.split(r'\n(\d+\.\s+\*\*(?:.+?)\*\*:)', content_after_indication_header)
    
    j = 1 
    while j < len(indications_raw):
        indication_title_line = indications_raw[j].strip()
        indication_details = indications_raw[j+1].strip() if (j+1) < len(indications_raw) else ""
        
        match = re.match(r'\d+\.\s+\*\*(.+?)\*\*:', indication_title_line)
        if match:
            clean_indication_name = match.group(1).strip()
            indications.append({
                "full_title": indication_title_line,
                "indication_category": clean_indication_name,
                "details": indication_details
            })
        j += 2 
    return indications

def parse_final_markdown_structure(markdown_text):
    doc_title = ""
    doc_intro_paragraph = ""
    general_conditions_map = {} 
    notes_map = {}
    all_drugs_data = {}

    # 1. Extract Document Title (H1) and intro paragraph
    h1_intro_match = re.match(r"^(#\s[^\n]+)\n+([^\n]+(?:(?!\n##|\n###)[^\n]*\n?)*)", markdown_text, re.MULTILINE)
    content_after_h1_intro = markdown_text

    if h1_intro_match:
        doc_title = h1_intro_match.group(1).strip()
        doc_intro_paragraph = h1_intro_match.group(2).strip()
        content_after_h1_intro = markdown_text[h1_intro_match.end():].strip()
    
    # 2. Isolate and process "## Obecné podmínky" block
    gc_block_regex = r"^## Obecné podmínky\n(.*?)(?=\n##\s|\Z)"
    general_conditions_block_match = re.search(gc_block_regex, content_after_h1_intro, re.DOTALL | re.MULTILINE)
    
    if general_conditions_block_match:
        gc_block_text_content = general_conditions_block_match.group(1).strip()
        h3_sections_in_gc = re.split(r'\n(?=###\s)', gc_block_text_content)
        for h3_section in h3_sections_in_gc:
            h3_section = h3_section.strip()
            if not h3_section.startswith("### "):
                continue
            
            h3_title_line_match = re.match(r"###\s([^\n]+)", h3_section)
            if h3_title_line_match:
                h3_title = h3_title_line_match.group(1).strip()
                h3_content = h3_section[h3_title_line_match.end():].strip()

                therapy_type_key = None
                is_notes = "poznámky k úhradě" in h3_title.lower()

                if "imunoterapie" in h3_title.lower():
                    therapy_type_key = "Imunoterapie"
                elif "cílené léčby" in h3_title.lower() or "cílené terapie" in h3_title.lower():
                    therapy_type_key = "Cílená léčba"
                
                if therapy_type_key:
                    if is_notes:
                        notes_map[therapy_type_key] = h3_content
                    else:
                        general_conditions_map[therapy_type_key] = h3_content
    
    # 3. Isolate and process "## Seznam léků" block
    drug_list_block_regex = r"^## Seznam léků\n(.*?)(?=\n##\s|\Z)"
    drug_list_block_match = re.search(drug_list_block_regex, content_after_h1_intro, re.DOTALL | re.MULTILINE)

    if drug_list_block_match:
        drug_list_content = drug_list_block_match.group(1).strip()
        drug_blocks_raw = re.split(r'\n(?=###\s\w+\s*\(?)', drug_list_content)

        for drug_block_text in drug_blocks_raw:
            drug_block_text = drug_block_text.strip()
            if not drug_block_text.startswith("### "): 
                continue

            first_line_end_idx = drug_block_text.find('\n')
            h3_drug_header_line = drug_block_text[4:].strip() if first_line_end_idx == -1 else drug_block_text[4:first_line_end_idx].strip()
            drug_specific_content_for_indications = "" if first_line_end_idx == -1 else drug_block_text[first_line_end_idx:].strip()
            
            drug_name_cleaned = re.sub(r'\s*\(.*?\)$', '', h3_drug_header_line).strip()

            if not drug_name_cleaned:
                continue
                
            drug_type = get_drug_type(drug_name_cleaned)
            indications = parse_indications_from_drug_content_h4(drug_specific_content_for_indications)
            
            if indications: 
                 all_drugs_data[drug_name_cleaned] = {
                    "type": drug_type,
                    "original_header": h3_drug_header_line, 
                    "indications": indications
                }
            
    return doc_title, doc_intro_paragraph, general_conditions_map, notes_map, all_drugs_data

def get_general_indication_category(specific_category):
    specific_category_lower = specific_category.lower()

    # Karcinom prsu
    if "karcinom prsu" in specific_category_lower:
        return "Karcinom prsu"
    
    # Karcinom plic
    if "karcinom plic" in specific_category_lower or "nsclc" in specific_category_lower: # NSCLC is a type of lung cancer
        return "Karcinom plic"

    # Karcinom ledvin
    if "renální karcinom" in specific_category_lower or "karcinom ledvin" in specific_category_lower:
        return "Karcinom ledvin"

    # Uroteliální karcinom
    if "uroteliální karcinom" in specific_category_lower:
        return "Uroteliální karcinom"

    # Melanom
    if "melanom" in specific_category_lower:
        return "Melanom"

    # Karcinom hlavy a krku
    if "karcinom hlavy a krku" in specific_category_lower:
        return "Karcinom hlavy a krku"

    # Kolorektální karcinom / Karcinom tlustého střeva nebo rekta
    if "kolorektální karcinom" in specific_category_lower or \
       "karcinom tlustého střeva nebo rekta" in specific_category_lower:
        return "Kolorektální karcinom"

    # Karcinom děložního hrdla
    if "karcinom děložního hrdla" in specific_category_lower:
        return "Karcinom děložního hrdla"

    # Hodgkinův lymfom
    if "hodgkinův lymfom" in specific_category_lower:
        return "Hodgkinův lymfom"

    # Karcinom jícnu nebo gastroezofageální junkce
    if "karcinom jícnu" in specific_category_lower or "gastroezofageální junkce" in specific_category_lower:
        return "Karcinom jícnu/GEJ"

    # Endometriální karcinom
    if "endometriální karcinom" in specific_category_lower:
        return "Endometriální karcinom"

    # Karcinom z Merkelových buněk
    if "karcinom z merkelových buněk" in specific_category_lower:
        return "Karcinom z Merkelových buněk"

    # Karcinom štítné žlázy
    if "karcinom štítné žlázy" in specific_category_lower or "medulární karcinom štítné žlázy" in specific_category_lower:
        return "Karcinom štítné žlázy"
    
    # Sarkom měkkých tkání
    if "sarkom měkkých tkání" in specific_category_lower:
        return "Sarkom měkkých tkání"

    # Karcinom vaječníku, vejcovodu nebo primárně peritoneální
    if "karcinom vaječníku" in specific_category_lower or \
       "karcinom vejcovodu" in specific_category_lower or \
       "peritoneální karcinom" in specific_category_lower or \
       "primárně peritoneální" in specific_category_lower: # check specific_category string as well
        return "Karcinom vaječníků/vejcovodů/peritonea"

    # Karcinom prostaty
    if "karcinom prostaty" in specific_category_lower:
        return "Karcinom prostaty"

    # Lymfomy/Leukémie (non-Hodgkin, CLL, etc.)
    hematological_keywords = [
        "folikulární lymfom", "dlbcl", "difúzní velkobuněčný", "lymfom z malých lymfocytů", "sll",
        "chronická lymfatická leukémie", "cll", "lymfom z plášťových buněk", 
        "lymfom marginální zóny", "malt", "burkittův lymfom", "akutní lymfoblastická leukémie",
        "lymfoblastový lymfom", "waldenströmova makroglobulinémie", 
        "b-buněčný lymfom s vysokým stupněm malignity" # For Lonkastuximab tesirin
    ]
    if any(keyword in specific_category_lower for keyword in hematological_keywords):
        return "Lymfomy/Leukémie (ostatní)"

    # Autoimunitní onemocnění (neonko)
    autoimmune_keywords = [
        "autoimunitní hemolytická anémie", "aiha", "imunitní trombocytopenická purpura", "itp",
        "trombotická trombocytopenická purpura", "ttp", "anca asociované vaskulitidy",
        "revmatoidní artritida", "membranózní glomerulonefritida"
    ]
    if any(keyword in specific_category_lower for keyword in autoimmune_keywords):
        return "Autoimunitní onemocnění (neonko)"
        
    # Default: return the original specific category if no general mapping found
    return specific_category

def get_display_indication_categories(all_drugs_data_dict):
    general_categories = set()
    if all_drugs_data_dict:
        for drug_data in all_drugs_data_dict.values():
            for ind_data in drug_data["indications"]:
                general_categories.add(get_general_indication_category(ind_data["indication_category"]))
    
    return ["Všechny indikace"] + sorted(list(general_categories))

def get_filtered_drug_names_final(all_drugs_data_dict, selected_therapy_filter="Všechny terapie"):
    drug_names = set()
    if all_drugs_data_dict:
        if selected_therapy_filter == "Všechny terapie":
            drug_names.update(all_drugs_data_dict.keys())
        else:
            for drug_name, data in all_drugs_data_dict.items():
                if data["type"] == selected_therapy_filter:
                    drug_names.add(drug_name)
    return ["Všechny léky"] + sorted(list(drug_names))

# --- Streamlit App UI ---
st.set_page_config(layout="wide", page_title="Přehled úhrad léčiv")

try:
    with open("uhrada.markdown", "r", encoding="utf-8") as f:
        markdown_content_file = f.read()
except FileNotFoundError:
    st.error("Soubor 'uhrada.markdown' nebyl nalezen.")
    st.stop()

doc_title_md, doc_intro_md, general_conditions_md, notes_md, all_drugs_md = parse_final_markdown_structure(markdown_content_file)

if doc_title_md:
    st.markdown(f"<h1>⚕️{doc_title_md}</h1>", unsafe_allow_html=True) 
if doc_intro_md:
    st.markdown(doc_intro_md)

if not all_drugs_md and not general_conditions_md and not notes_md:
    st.error("Nepodařilo se zpracovat žádná data z Markdown souboru. Zkontrolujte jeho strukturu (očekává se H1 titul, H2 'Obecné podmínky', H2 'Seznam léků').")
    st.stop()
elif not all_drugs_md and (general_conditions_md or notes_md):
    st.warning("Nebyly nalezeny žádné informace o lécích v sekci '## Seznam léků'. Zobrazují se pouze obecné podmínky/poznámky.")


st.sidebar.header("Filtry")

therapy_types_present = sorted(list(set(general_conditions_md.keys()) | set(notes_md.keys())))
therapy_types_for_filter = ["Všechny terapie"] + therapy_types_present
selected_therapy_type = st.sidebar.selectbox("Vyberte typ terapie:", therapy_types_for_filter)

drugs_for_select = get_filtered_drug_names_final(all_drugs_md, selected_therapy_type)
selected_drug = st.sidebar.selectbox("Vyberte lék:", drugs_for_select)

# Use the new function for general indication categories
indication_categories_list = get_display_indication_categories(all_drugs_md)
selected_general_indication_category = st.sidebar.selectbox("Vyberte typ diagnózy (indikace):", indication_categories_list)

st.markdown("---")

# Display General Conditions and Notes
gc_notes_displayed_flag = False
expand_gc_notes = True 

if selected_therapy_type == "Všechny terapie":
    expand_gc_notes = False 
    for therapy_key_display in therapy_types_present: 
        if therapy_key_display in general_conditions_md:
            with st.expander(f"📋 Obecné podmínky pro úhradu – {therapy_key_display}", expanded=expand_gc_notes):
                st.markdown(general_conditions_md[therapy_key_display])
                gc_notes_displayed_flag = True
        if therapy_key_display in notes_md:
             with st.expander(f"📝 Poznámky k úhradě – {therapy_key_display}", expanded=expand_gc_notes):
                st.markdown(notes_md[therapy_key_display])
                gc_notes_displayed_flag = True
else: 
    if selected_therapy_type in general_conditions_md:
        with st.expander(f"📋 Obecné podmínky pro úhradu – {selected_therapy_type}", expanded=expand_gc_notes):
            st.markdown(general_conditions_md[selected_therapy_type])
            gc_notes_displayed_flag = True
    if selected_therapy_type in notes_md:
        with st.expander(f"📝 Poznámky k úhradě – {selected_therapy_type}", expanded=expand_gc_notes):
            st.markdown(notes_md[selected_therapy_type])
            gc_notes_displayed_flag = True

if not gc_notes_displayed_flag and (general_conditions_md or notes_md):
    st.info("Pro aktuálně zvolený filtr typu terapie nebyly nalezeny specifické obecné podmínky ani poznámky, nebo v dokumentu nejsou definovány.")
elif not general_conditions_md and not notes_md:
    st.info("V dokumentu nebyly nalezeny žádné obecné podmínky ani poznámky v sekci '## Obecné podmínky'.")


# Display Drug Information
drugs_to_show_list = []
if all_drugs_md: 
    if selected_drug == "Všechny léky":
        for drug_name_iter, data_iter in all_drugs_md.items():
            if selected_therapy_type == "Všechny terapie" or data_iter["type"] == selected_therapy_type:
                drugs_to_show_list.append(drug_name_iter)
        drugs_to_show_list.sort() 
    else: 
        if selected_drug in all_drugs_md:
            drug_data_check = all_drugs_md[selected_drug]
            if selected_therapy_type == "Všechny terapie" or drug_data_check["type"] == selected_therapy_type:
                drugs_to_show_list.append(selected_drug)

results_found_for_drugs_display = False
if drugs_to_show_list:
    for drug_name_to_display in drugs_to_show_list:
        current_drug_data = all_drugs_md[drug_name_to_display]
        
        indications_to_display_for_this_drug = []
        if selected_general_indication_category == "Všechny indikace":
            indications_to_display_for_this_drug = current_drug_data["indications"]
        else:
            for ind_specific in current_drug_data["indications"]:
                drug_specific_indication_general_form = get_general_indication_category(ind_specific["indication_category"])
                if drug_specific_indication_general_form == selected_general_indication_category:
                    indications_to_display_for_this_drug.append(ind_specific)
        
        if indications_to_display_for_this_drug:
            results_found_for_drugs_display = True
            
            drug_header_display = current_drug_data.get("original_header", drug_name_to_display)
            st.markdown(f"### 💊 {drug_header_display} <font size='3'>(Typ: {current_drug_data['type']})</font>", unsafe_allow_html=True)

            for ind_data_item_display in indications_to_display_for_this_drug:
                st.markdown(f"**{ind_data_item_display['full_title']}**")
                detail_lines_display = ind_data_item_display['details'].split('\n')
                formatted_details_display = [re.sub(r'^\s*-\s+', '* ', line) for line in detail_lines_display]
                st.markdown("\n".join(formatted_details_display))
                st.markdown("---") 
elif all_drugs_md: 
    st.info("Pro aktuální kombinaci filtrů (typ terapie, lék) nebyly nalezeny žádné léky k zobrazení.")


if drugs_to_show_list and not results_found_for_drugs_display:
    st.info("Pro vybrané léky nebyly nalezeny žádné indikace odpovídající filtru diagnózy.")


st.sidebar.markdown("---")
st.sidebar.info("Aplikace pro přehled podmínek úhrady léčiv.")

