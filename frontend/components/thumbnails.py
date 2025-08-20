import streamlit as st
from PIL import Image
import io
from config import THUMBNAIL_WIDTH, ESTIMATED_CONTENT_WIDTH, MIN_COLUMNS, MAX_COLUMNS
from utils.helpers import calculate_columns


def display_uploaded_thumbnails(files_list):
    if not files_list:
        st.info("Файлы не выбраны.")
        return

    num_columns = calculate_columns(THUMBNAIL_WIDTH, ESTIMATED_CONTENT_WIDTH, MIN_COLUMNS, MAX_COLUMNS)

    total_files = len(files_list)
    files_to_remove_indices = []

    for i in range(0, total_files, num_columns):
        cols = st.columns(num_columns) 
        for j in range(num_columns):
            idx = i + j
            if idx < total_files: 
                uploaded_file_obj = files_list[idx]
                file_unique_id = uploaded_file_obj.get("unique_id")
                
                with cols[j]: 
                    try:
                        st.markdown(f"<small>{uploaded_file_obj['name'][:20]}</small>", unsafe_allow_html=True)
                        
                        if (uploaded_file_obj["type"] and 
                            uploaded_file_obj["type"].startswith('image/')):
                            image_bytes = uploaded_file_obj["file_obj"].getvalue() 
                            image = Image.open(io.BytesIO(image_bytes))
                            image.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_WIDTH * 2))
                            st.image(image, width=THUMBNAIL_WIDTH) 
                        else:
                            st.info(f"Файл: {uploaded_file_obj['type'] or 'Неизвестный тип'}")
                        
                        if st.button("Удалить", key=f"del_btn_{file_unique_id}"):
                            files_to_remove_indices.append(idx)
                            
                    except Exception as e:
                        st.error(f"Ошибка отображения {uploaded_file_obj['name']}: {e}")
            else:
                with cols[j]:
                    st.empty() 

    if files_to_remove_indices:
        files_to_remove_indices.sort(reverse=True)
        for idx in files_to_remove_indices:
            if 0 <= idx < len(st.session_state.selected_files):
                st.session_state.selected_files.pop(idx)
        
        st.rerun() 
