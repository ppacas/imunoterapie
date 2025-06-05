import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

# Configure page
st.set_page_config(
    layout="wide", 
    page_title="Přehled úhrad léčiv",
    page_icon="⚕️",
    menu_items={
        'About': "Aplikace pro přehled podmínek úhrady onkologických léčiv v ČR"
    }
)

# Load and cache data
@st.cache_data
def load_drug_data():
    """Load drug data from JSON file"""
    try:
        with open("uhrada.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Soubor 'uhrada.json' nebyl nalezen.")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Chyba při čtení JSON souboru: {e}")
        return None

@st.cache_data
def get_drug_type(drug_name):
    """Determine if drug is immunotherapy or targeted therapy"""
    immunotherapy_keywords = [
        "mab", "lumab", "zumab", "ximab", "tumab", "mumab"
    ]
    # Check if drug name ends with common immunotherapy suffixes
    drug_lower = drug_name.lower()
    for keyword in immunotherapy_keywords:
        if keyword in drug_lower:
            return "Imunoterapie"
    return "Cílená léčba"

@st.cache_data
def get_general_indication_category(condition):
    """Map specific conditions to general indication categories"""
    condition_lower = condition.lower()
    
    mappings = {
        "Karcinom prsu": ["karcinom prsu", "her2", "triple-negativní"],
        "Karcinom plic": ["karcinom plic", "nsclc", "malobuněčný karcinom plic"],
        "Karcinom ledvin": ["renální karcinom", "karcinom ledvin", "světlobuněčný karcinom ledvin"],
        "Uroteliální karcinom": ["uroteliální karcinom"],
        "Melanom": ["melanom"],
        "Karcinom hlavy a krku": ["karcinom hlavy a krku", "skvamózní karcinom", "dutina ústní", "faryng", "larynx"],
        "Kolorektální karcinom": ["kolorektální karcinom", "karcinom tlustého střeva", "karcinom rekta"],
        "Karcinom děložního hrdla": ["karcinom děložního hrdla", "karcinom děložního čípku"],
        "Hodgkinův lymfom": ["hodgkinův lymfom"],
        "Karcinom jícnu/GEJ": ["karcinom jícnu", "gastroezofageální junkce"],
        "Endometriální karcinom": ["endometriální karcinom"],
        "Karcinom z Merkelových buněk": ["karcinom z merkelových buněk"],
        "Karcinom štítné žlázy": ["karcinom štítné žlázy", "medulární karcinom štítné žlázy"],
        "Sarkom měkkých tkání": ["sarkom měkkých tkání"],
        "Karcinom vaječníků/vejcovodů/peritonea": ["karcinom vaječníku", "karcinom vejcovodu", "peritoneální", "primárně peritoneální"],
        "Karcinom prostaty": ["karcinom prostaty"],
        "Hepatocelulární karcinom": ["hepatocelulární karcinom"],
        "Lymfomy/Leukémie": ["lymfom", "leukémie", "dlbcl", "folikulární", "cll", "sll", "burkittův", "waldenströmova"],
        "Autoimunitní onemocnění": ["autoimunitní", "aiha", "itp", "ttp", "vaskulitidy", "revmatoidní artritida", "glomerulonefritida"]
    }
    
    for category, keywords in mappings.items():
        if any(keyword in condition_lower for keyword in keywords):
            return category
    
    return "Ostatní"

def search_drugs(drugs_data, search_term):
    """Search drugs by name, indication, or criteria"""
    if not search_term:
        return drugs_data
    
    search_lower = search_term.lower()
    filtered_drugs = []
    
    for drug in drugs_data:
        # Search in drug name
        if search_lower in drug["name"].lower():
            filtered_drugs.append(drug)
            continue
        
        # Search in indications
        for indication in drug.get("indications", []):
            found = False
            if search_lower in indication.get("condition", "").lower():
                found = True
            else:
                for detail in indication.get("details", []):
                    if search_lower in str(detail.get("criteria", "")).lower() or \
                       search_lower in str(detail.get("therapy_type", "")).lower():
                        found = True
                        break
            if found:
                filtered_drugs.append(drug)
                break
    
    return filtered_drugs

def create_summary_dashboard(drugs_data):
    """Create visual summary dashboard"""
    st.markdown("## 📊 Přehled statistik")
    
    # Calculate statistics
    total_drugs = len(drugs_data)
    drug_types = {}
    indication_counts = {}
    therapy_line_counts = {"1. linie": 0, "2. linie": 0, "Adjuvantní": 0, "Udržovací": 0}
    
    for drug in drugs_data:
        # Count drug types
        drug_type = get_drug_type(drug["name"])
        drug_types[drug_type] = drug_types.get(drug_type, 0) + 1
        
        # Count indications
        for indication in drug.get("indications", []):
            general_cat = get_general_indication_category(indication["condition"])
            indication_counts[general_cat] = indication_counts.get(general_cat, 0) + 1
            
            # Count therapy lines
            for detail in indication.get("details", []):
                therapy_type = detail.get("therapy_type", "").lower()
                if "1. linie" in therapy_type:
                    therapy_line_counts["1. linie"] += 1
                elif "2. linie" in therapy_type:
                    therapy_line_counts["2. linie"] += 1
                elif "adjuvantní" in therapy_type:
                    therapy_line_counts["Adjuvantní"] += 1
                elif "udržovací" in therapy_type:
                    therapy_line_counts["Udržovací"] += 1
    
    # Create columns for metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Celkem léků", total_drugs)
    with col2:
        st.metric("Imunoterapie", drug_types.get("Imunoterapie", 0))
    with col3:
        st.metric("Cílená léčba", drug_types.get("Cílená léčba", 0))
    with col4:
        st.metric("Unikátní indikace", len(indication_counts))
    
    # Create visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Therapy type pie chart
        fig_pie = px.pie(
            values=list(drug_types.values()),
            names=list(drug_types.keys()),
            title="Rozdělení podle typu terapie",
            color_discrete_map={'Imunoterapie': '#1f77b4', 'Cílená léčba': '#ff7f0e'}
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Therapy line distribution
        fig_bar = px.bar(
            x=list(therapy_line_counts.keys()),
            y=list(therapy_line_counts.values()),
            title="Rozdělení podle linie léčby",
            labels={'x': 'Typ léčby', 'y': 'Počet indikací'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Top indications bar chart
    st.markdown("### Top 10 indikací podle počtu léků")
    top_indications = sorted(indication_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    if top_indications:
        fig_bar2 = px.bar(
            x=[count for _, count in top_indications],
            y=[name for name, _ in top_indications],
            orientation='h',
            title="Nejčastější indikace",
            labels={'x': 'Počet léků', 'y': 'Indikace'}
        )
        fig_bar2.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_bar2, use_container_width=True)

def create_export_dataframe(drugs_to_show, selected_indication_filter=None):
    """Create a DataFrame from filtered drug data for export"""
    export_data = []
    
    for drug in drugs_to_show:
        drug_type = get_drug_type(drug["name"])
        
        for indication in drug.get("indications", []):
            general_cat = get_general_indication_category(indication["condition"])
            
            # Filter by indication if specified
            if selected_indication_filter and selected_indication_filter != "Všechny indikace":
                if general_cat != selected_indication_filter:
                    continue
            
            for detail in indication.get("details", []):
                export_data.append({
                    "Název léku": drug["name"],
                    "Typ terapie": drug_type,
                    "Indikace": indication["condition"],
                    "Obecná kategorie": general_cat,
                    "Typ léčby": detail.get("therapy_type", ""),
                    "Kritéria": str(detail.get("criteria", "")),
                    "Dodatečné podmínky": str(detail.get("additional_conditions", "")),
                    "Úhrada": detail.get("reimbursement", "")
                })
    
    return pd.DataFrame(export_data)

def display_drug_info(drug, selected_indication_filter=None):
    """Display formatted drug information"""
    drug_type = get_drug_type(drug["name"])
    
    st.markdown(f"### 💊 {drug['name']} <font size='3'>(Typ: {drug_type})</font>", 
                unsafe_allow_html=True)
    
    for indication in drug.get("indications", []):
        general_cat = get_general_indication_category(indication["condition"])
        
        # Filter by indication if specified
        if selected_indication_filter and selected_indication_filter != "Všechny indikace":
            if general_cat != selected_indication_filter:
                continue
        
        st.markdown(f"**{indication['condition']}**")
        
        for detail in indication.get("details", []):
            if detail.get("therapy_type"):
                st.markdown(f"**{detail['therapy_type']}:**")
            
            # Display criteria
            criteria = detail.get("criteria", "")
            if isinstance(criteria, list):
                for criterion in criteria:
                    st.markdown(f"• {criterion}")
            else:
                st.markdown(f"• {criteria}")
            
            # Display additional conditions
            additional = detail.get("additional_conditions", [])
            if additional:
                st.markdown("**Další podmínky:**")
                if isinstance(additional, list):
                    for condition in additional:
                        st.markdown(f"  - {condition}")
                else:
                    st.markdown(f"  - {additional}")
            
            # Display reimbursement info
            if detail.get("reimbursement"):
                st.markdown(f"**Úhrada:** {detail['reimbursement']}")
        
        st.markdown("---")

def display_general_conditions(data):
    """Display general conditions for drug reimbursement"""
    col1, col2 = st.columns(2)
    
    with col1:
        if "immunotherapy" in data.get("general_conditions", {}):
            with st.expander("📋 Imunoterapie - obecné podmínky", expanded=True):
                gc = data["general_conditions"]["immunotherapy"]
                
                for key, value in gc.items():
                    if key == "organ_function":
                        st.markdown("**Funkce orgánů:**")
                        for organ, requirements in value.items():
                            st.markdown(f"  • **{organ.replace('_', ' ').title()}:**")
                            if isinstance(requirements, dict):
                                for req_key, req_val in requirements.items():
                                    st.markdown(f"    - {req_key}: {req_val}")
                            else:
                                st.markdown(f"    - {requirements}")
                    elif key == "autoimmune_diseases":
                        st.markdown(f"**Autoimunitní onemocnění:** {value.get('general', '')}")
                        if value.get("exceptions"):
                            st.markdown("  Výjimky:")
                            for exc in value["exceptions"]:
                                st.markdown(f"  - {exc}")
                    else:
                        st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
                
                if "immunotherapy_notes" in data["general_conditions"]:
                    st.markdown("**Poznámky:**")
                    notes = data["general_conditions"]["immunotherapy_notes"]
                    for key, value in notes.items():
                        st.markdown(f"• **{key.replace('_', ' ').title()}:** {value}")
    
    with col2:
        if "targeted_therapy" in data.get("general_conditions", {}):
            with st.expander("📋 Cílená léčba - obecné podmínky", expanded=True):
                gc = data["general_conditions"]["targeted_therapy"]
                
                for key, value in gc.items():
                    st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
                
                if "targeted_therapy_notes" in data["general_conditions"]:
                    st.markdown("**Poznámky:**")
                    notes = data["general_conditions"]["targeted_therapy_notes"]
                    for key, value in notes.items():
                        st.markdown(f"• **{key.replace('_', ' ').title()}:** {value}")

def compare_drugs(drugs_to_compare, all_drugs_data):
    """Create drug comparison view"""
    st.markdown("## 🔄 Porovnání vybraných léků")
    
    # Find drugs in data
    drugs_data = []
    for drug_name in drugs_to_compare:
        for drug in all_drugs_data:
            if drug["name"] == drug_name:
                drugs_data.append(drug)
                break
    
    if not drugs_data:
        st.error("Vybrané léky nebyly nalezeny v databázi.")
        return
    
    # Create columns for comparison
    cols = st.columns(len(drugs_data))
    
    for idx, drug in enumerate(drugs_data):
        with cols[idx]:
            drug_type = get_drug_type(drug["name"])
            
            # Drug header
            st.markdown(f"### {drug['name']}")
            st.markdown(f"**Typ:** {drug_type}")
            
            # Count indications
            indication_count = len(drug.get("indications", []))
            st.metric("Počet indikací", indication_count)
            
            # List indications
            st.markdown("**Indikace:**")
            for i, indication in enumerate(drug.get("indications", []), 1):
                general_cat = get_general_indication_category(indication["condition"])
                st.markdown(f"{i}. {general_cat}")
                
                # Show details in expander
                with st.expander(f"Detail: {indication['condition']}"):
                    for detail in indication.get("details", []):
                        if detail.get("therapy_type"):
                            st.markdown(f"**{detail['therapy_type']}**")
                        if detail.get("criteria"):
                            st.markdown(f"- {detail['criteria']}")
    
    # Common indications analysis
    st.markdown("### 🔍 Společné indikace")
    
    # Find common indication categories
    indication_sets = []
    for drug in drugs_data:
        drug_indications = set(
            get_general_indication_category(ind["condition"])
            for ind in drug.get("indications", [])
        )
        indication_sets.append(drug_indications)
    
    common_indications = set.intersection(*indication_sets) if indication_sets else set()
    
    if common_indications:
        st.success(f"Společné indikace: {', '.join(sorted(common_indications))}")
    else:
        st.info("Vybrané léky nemají žádné společné indikace.")
    
    # Create comparison table
    st.markdown("### 📋 Tabulka porovnání")
    
    comparison_data = []
    all_indication_categories = sorted(set(
        get_general_indication_category(ind["condition"])
        for drug in drugs_data
        for ind in drug.get("indications", [])
    ))
    
    for indication_cat in all_indication_categories:
        row = {"Indikace": indication_cat}
        for drug in drugs_data:
            has_indication = any(
                get_general_indication_category(ind["condition"]) == indication_cat
                for ind in drug.get("indications", [])
            )
            row[drug["name"]] = "✓" if has_indication else "✗"
        comparison_data.append(row)
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Style the dataframe
    def style_comparison_table(val):
        if val == "✓":
            return 'background-color: #90EE90'
        elif val == "✗":
            return 'background-color: #FFB6C1'
        return ''
    
    styled_df = comparison_df.style.applymap(
        style_comparison_table,
        subset=[drug["name"] for drug in drugs_data]
    )
    
    st.dataframe(styled_df, use_container_width=True)

# Main app
def main():
    # Load data
    data = load_drug_data()
    
    if not data:
        st.stop()
    
    # Display header
    st.markdown(f"<h1>⚕️ {data['title']}</h1>", unsafe_allow_html=True)
    st.markdown(data.get('description', ''))
    
    # Sidebar
    st.sidebar.header("🔍 Filtry")
    
    # Therapy type filter
    therapy_types = ["Všechny terapie", "Imunoterapie", "Cílená léčba"]
    selected_therapy = st.sidebar.selectbox("Vyberte typ terapie:", therapy_types)
    
    # Get all indication categories
    all_indication_categories = set()
    for drug in data.get("drugs", []):
        for indication in drug.get("indications", []):
            all_indication_categories.add(get_general_indication_category(indication["condition"]))
    
    indication_categories = ["Všechny indikace"] + sorted(list(all_indication_categories))
    selected_indication = st.sidebar.selectbox("Vyberte typ diagnózy:", indication_categories)
    
    # Search
    search_term = st.sidebar.text_input("🔍 Vyhledat (název léku, indikace, kritéria):", "")
    
    # Drug comparison
    st.sidebar.markdown("---")
    st.sidebar.header("🔄 Porovnání léků")
    
    available_drugs = [drug["name"] for drug in data.get("drugs", [])]
    drugs_to_compare = st.sidebar.multiselect(
        "Vyberte léky k porovnání (max 3):",
        available_drugs,
        max_selections=3
    )
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Přehled léků", "📊 Dashboard", "📑 Obecné podmínky", "🔄 Porovnání"])
    
    with tab1:
        # Filter drugs
        filtered_drugs = data.get("drugs", [])
        
        # Apply therapy type filter
        if selected_therapy != "Všechny terapie":
            filtered_drugs = [
                d for d in filtered_drugs 
                if get_drug_type(d["name"]) == selected_therapy
            ]
        
        # Apply indication filter
        if selected_indication != "Všechny indikace":
            filtered_drugs = [
                d for d in filtered_drugs 
                if any(
                    get_general_indication_category(ind["condition"]) == selected_indication 
                    for ind in d.get("indications", [])
                )
            ]
        
        # Apply search
        if search_term:
            filtered_drugs = search_drugs(filtered_drugs, search_term)
        
        # Display results
        st.markdown(f"### Nalezené léky ({len(filtered_drugs)})")
        
        if filtered_drugs:
            # Export buttons
            col1, col2, col3 = st.columns([1, 1, 8])
            
            with col1:
                df = create_export_dataframe(filtered_drugs, selected_indication)
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📊 Export CSV",
                    data=csv,
                    file_name=f"uhrada_lecby_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='Úhrada léčby', index=False)
                    workbook = writer.book
                    worksheet = writer.sheets['Úhrada léčby']
                    # Auto-adjust columns' width
                    for column in df:
                        column_width = max(df[column].astype(str).map(len).max(), len(column))
                        col_idx = df.columns.get_loc(column)
                        worksheet.set_column(col_idx, col_idx, min(column_width + 2, 50))
                
                st.download_button(
                    label="📑 Export Excel",
                    data=buffer.getvalue(),
                    file_name=f"uhrada_lecby_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            st.markdown("---")
            
            # Display drugs
            for drug in filtered_drugs:
                display_drug_info(drug, selected_indication if selected_indication != "Všechny indikace" else None)
        else:
            st.info("Pro zvolené filtry nebyly nalezeny žádné léky.")
    
    with tab2:
        if data.get("drugs"):
            create_summary_dashboard(data["drugs"])
        else:
            st.warning("Nejsou k dispozici žádná data pro zobrazení statistik.")
    
    with tab3:
        display_general_conditions(data)
    
    with tab4:
        if drugs_to_compare and len(drugs_to_compare) >= 2:
            compare_drugs(drugs_to_compare, data.get("drugs", []))
        else:
            st.info("Vyberte alespoň 2 léky k porovnání v levém panelu.")

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info("⚕️ Aplikace pro přehled podmínek úhrady onkologických léčiv v ČR")
    
    # Add timestamp if available
    with st.sidebar:
        if "last_updated" in data:
            st.caption(f"Poslední aktualizace dat: {data['last_updated']}")

if __name__ == "__main__":
    main()
