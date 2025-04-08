
import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Option Analizi", layout="wide")
st.title("🧩 Mağaza Option Çeşitliliği ve Dağılım Önerisi")

uploaded_file = st.file_uploader("Excel dosyanı yükle (.xlsx)", type="xlsx")

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    for col in ['Stok Adedi', 'Rezerve Adet', 'Satış Adedi', 'Lot İçi']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['Toplam Stok'] = df['Stok Adedi'] + df['Rezerve Adet']

    df['Lokasyon Türü'] = df['Lokasyon Türü'].astype(str).str.lower().str.strip()
    df_magaza = df[df['Lokasyon Türü'] == 'mağaza']
    df_depo = df[df['Lokasyon Türü'] == 'depo']

    option_count = df_magaza.groupby('Mağaza')['Ürün Kodu'].nunique().reset_index()
    option_count.columns = ['Mağaza', 'Toplam Option']
    sku_avg = df_magaza.groupby(['Mağaza', 'Ürün Kodu']).size().groupby('Mağaza').mean().reset_index(name='Ortalama SKU/Option')

    bestseller = df_magaza.groupby('Ürün Kodu')['Satış Adedi'].sum().reset_index().sort_values(by='Satış Adedi', ascending=False)
    bestseller['Kümülatif'] = bestseller['Satış Adedi'].cumsum()
    total_sales = bestseller['Satış Adedi'].sum()
    bestseller['Kümülatif %'] = bestseller['Kümülatif'] / total_sales
    bestseller_top = bestseller[bestseller['Kümülatif %'] <= 0.8]['Ürün Kodu']
    bestseller_coverage = df_magaza[df_magaza['Ürün Kodu'].isin(bestseller_top)].groupby('Mağaza')['Ürün Kodu'].nunique().reset_index()
    bestseller_coverage.columns = ['Mağaza', 'Bestseller Option Kapsaması']

    depo_options = df_depo[df_depo['Toplam Stok'] > 0]['Ürün Kodu'].unique()
    magaza_option_set = df_magaza.groupby('Mağaza')['Ürün Kodu'].unique().to_dict()

    eksik_rows = []
    for magaza, mevcutlar in magaza_option_set.items():
        eksikler = set(depo_options) - set(mevcutlar)
        for urun in eksikler:
            detay = df_depo[df_depo['Ürün Kodu'] == urun].iloc[0]
            eksik_rows.append({
                'Mağaza': magaza,
                'Ürün Kodu': urun,
                'Kategori': detay['Kategori'],
                'Altkategori': detay['Altkategori'],
                'Lot Adı': detay['Lot Adı'],
                'Stok Adedi': detay['Stok Adedi'],
                'Satış Adedi': detay['Satış Adedi'],
                'Rezerve Adet': detay['Rezerve Adet'],
                'Lot İçi': detay['Lot İçi']
            })

    depo_stok_dict = df_depo.groupby('Ürün Kodu')['Toplam Stok'].sum().to_dict()
    for row in eksik_rows:
        urun = row['Ürün Kodu']
        lot_ici = row['Lot İçi']
        if depo_stok_dict.get(urun, 0) >= lot_ici:
            row['Öneri Dağılım Adedi'] = lot_ici
            depo_stok_dict[urun] -= lot_ici
        else:
            row['Öneri Dağılım Adedi'] = 0

    eksik_df = pd.DataFrame(eksik_rows)
    final = option_count.merge(sku_avg, on='Mağaza', how='left')                        .merge(bestseller_coverage, on='Mağaza', how='left')

    st.subheader("📊 Genel Özet")
    st.dataframe(final)

    st.subheader("🏪 Mağazadaki Eksik Optionlar")
    st.dataframe(eksik_df)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        final.to_excel(writer, sheet_name='Genel Özet', index=False)
        eksik_df.to_excel(writer, sheet_name='Mağazadaki Eksik Optionlar', index=False)
    output.seek(0)
    st.download_button("📥 Excel İndir", data=output, file_name="option_analizi_sonuclar.xlsx")
