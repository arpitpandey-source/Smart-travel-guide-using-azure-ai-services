import streamlit as st
import requests
import openai
import json
import os
from datetime import datetime, date
import pytz
import hashlib

# ─── PAGE CONFIG ──────────────────────────────────────────────
st.set_page_config(page_title="Wanderlust Pro", page_icon="🧭", layout="wide")

# ─── CUSTOM CSS ───────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {font-size:2.5rem; font-weight:700; color:#1E88E5;}
    .sub-header {font-size:1.3rem; color:#424242;}
    .metric-card {background:#E3F2FD; padding:15px; border-radius:10px; border-left:4px solid #1E88E5;}
    .warning-card {background:#FFF3E0; padding:15px; border-radius:10px; border-left:4px solid #FF9800;}
    .success-card {background:#E8F5E9; padding:15px; border-radius:10px; border-left:4px solid #4CAF50;}
    .stTabs [data-baseweb="tab-list"] {gap:8px;}
    .stTabs [data-baseweb="tab"] {padding:10px 20px; border-radius:8px 8px 0 0;}
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR: API KEYS & NAVIGATION ──────────────────────────
with st.sidebar:
    st.markdown("## 🧭 Wanderlust Pro")
    st.divider()

    # Navigation
    st.session_state['current_page'] = st.radio(
        "Go to", [
            "📸 Image Analyzer",
            "🗺️ Trip Planner",
            "💰 Budget Tracker",
            "📋 Packing List",
            "🌤️ Weather",
            "💱 Currency",
            "🆘 Emergency Info",
            "⚙️ Settings"
        ],
        index=0
    )

    st.divider()
    st.caption("### API Configuration")

    # API Keys (collapsible in settings)
    if 'api_keys' not in st.session_state:
        st.session_state['api_keys'] = {
            'vision_key': '', 'vision_endpoint': '', 'translator_key':  '',
            'translator_region': '', 'groq_key': ''
        }

    # Auto-save API keys from settings page
    settings_tab = st.session_state.get('_settings_tab', None)

    with st.expander("🔑 API Keys", expanded=False):
        st.session_state['api_keys']['vision_key'] = st.text_input(
            "Azure Vision Key", value=st.session_state['api_keys'].get('vision_key',''),
            type="password", key="vision_key_input"
        )
        st.session_state['api_keys']['vision_endpoint'] = st.text_input(
            "Azure Vision Endpoint", value=st.session_state['api_keys'].get('vision_endpoint',''),
            placeholder="https://your-resource.cognitiveservices.azure.com/", key="vision_ep_input"
        )
        st.session_state['api_keys']['translator_key'] = st.text_input(
            "Azure Translator Key", value=st.session_state['api_keys'].get('translator_key',''),
            type="password", key="trans_key_input"
        )
        st.session_state['api_keys']['translator_region'] = st.text_input(
            "Translator Region", value=st.session_state['api_keys'].get('translator_region',''),
            placeholder="e.g. centralindia", key="trans_region_input"
        )
        st.session_state['api_keys']['groq_key'] = st.text_input(
            "Groq API Key (free at console.groq.com)", value=st.session_state['api_keys'].get('groq_key',''),
            type="password", key="groq_key_input"
        )

# ─── DATA PERSISTENCE ─────────────────────────────────────────
DATA_DIR = "travel_data"
os.makedirs(DATA_DIR, exist_ok=True)

def get_file_path(name): return os.path.join(DATA_DIR, f"{name}.json")

def load_data(name, default):
    try:
        with open(get_file_path(name), 'r') as f: return json.load(f)
    except: return default

def save_data(name, data):
    with open(get_file_path(name), 'w') as f: json.dump(data, f, default=str)

# ─── SESSION STATE INIT ───────────────────────────────────────
defaults = {
    'description_text': '', 'chat_history': [], 'current_trip': None,
    'trips': [], 'expenses': [], 'packing_items': [], 'selected_destination': '',
    'currency_from': 'USD', 'currency_to': 'EUR', 'currency_amount': 100,
    'emergency_country': 'France'
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# Load persisted data
st.session_state['trips'] = load_data('trips', [])
st.session_state['expenses'] = load_data('expenses', [])
st.session_state['packing_items'] = load_data('packing_items', [])

# ═══════════════════════════════════════════════════════════════
# PAGE: IMAGE ANALYZER
# ═══════════════════════════════════════════════════════════════
if st.session_state['current_page'] == "📸 Image Analyzer":
    st.markdown('<p class="main-header">📸 Image Analyzer</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload travel photos and get AI-powered insights</p>', unsafe_allow_html=True)
    st.divider()

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded_file = st.file_uploader("Upload a travel image", type=["jpg", "jpeg", "png", "webp"])

        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)

            if st.button("🔍 Analyze Image", type="primary"):
                vision_key = st.session_state['api_keys']['vision_key']
                vision_endpoint = st.session_state['api_keys']['vision_endpoint']

                if not vision_key or not vision_endpoint:
                    st.error("Please enter Azure Vision credentials in the sidebar.")
                else:
                    with st.spinner("Analyzing image…"):
                        endpoint_clean = vision_endpoint.rstrip("/")
                        url = f"{endpoint_clean}/vision/v3.2/analyze?visualFeatures=Description,Tags,Objects,Faces,Color"
                        headers = {
                            "Ocp-Apim-Subscription-Key": vision_key,
                            "Content-Type": "application/octet-stream",
                        }
                        response = requests.post(url, headers=headers, data=uploaded_file.read())

                    if response.status_code != 200:
                        st.error(f"Vision API error {response.status_code}: {response.text}")
                    else:
                        result = response.json()
                        captions = result.get("description", {}).get("captions", [])
                        st.session_state.description_text = captions[0]["text"] if captions else "No description found."
                        tags = [t["name"] for t in result.get("tags", [])]

                        st.session_state['analyzed_tags'] = tags
                        st.session_state['analyzed_caption'] = st.session_state.description_text

                        # Auto-detect destination from tags
                        known_places = ['beach', 'mountain', 'city', 'temple', 'church', 'museum',
                                       'park', 'tower', 'bridge', 'palace', 'ruins', 'forest',
                                       'desert', 'lake', 'waterfall', 'castle', 'monument']
                        detected = [t for t in tags if t.lower() in known_places]
                        if detected:
                            st.session_state['selected_destination'] = detected[0].title()

                        st.success("✅ Image analyzed successfully!")

    with col2:
        if st.session_state.description_text:
            st.markdown("### 🧠 Analysis Results")
            st.info(f"**Description:** {st.session_state.description_text}")

            if st.session_state.get('analyzed_tags'):
                st.markdown("**Tags:**")
                cols = st.columns(4)
                for i, tag in enumerate(st.session_state['analyzed_tags'][:12]):
                    cols[i%4].badge(tag)

            # Quick actions
            st.divider()
            st.markdown("### 🚀 Quick Actions")

            if st.session_state.get('analyzed_tags'):
                detected_place = st.session_state['analyzed_tags'][0].title() if st.session_state['analyzed_tags'] else ''
                if st.button(f"📋 Create trip to {detected_place}", use_container_width=True):
                    new_trip = {
                        'id': hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8],
                        'name': f"Trip to {detected_place}",
                        'destination': detected_place,
                        'start_date': str(date.today()),
                        'end_date': str(date.today()),
                        'places': [],
                        'notes': ''
                    }
                    st.session_state['trips'].append(new_trip)
                    save_data('trips', st.session_state['trips'])
                    st.success(f"Trip to {detected_place} created!")

    # Translation Section
    st.divider()
    st.subheader("🌍 Translate Description")

    lang_options = {
        "Spanish": "es", "French": "fr", "German": "de", "Italian": "it",
        "Portuguese": "pt", "Japanese": "ja", "Chinese": "zh-Hans",
        "Korean": "ko", "Arabic": "ar", "Hindi": "hi", "Russian": "ru",
        "Thai": "th", "Vietnamese": "vi", "Indonesian": "id"
    }

    trans_col1, trans_col2, trans_col3 = st.columns([2, 1, 1])
    with trans_col1:
        selected_lang = st.selectbox("Translate to", list(lang_options.keys()))
    with trans_col2:
        st.write("")  # spacing
    with trans_col3:
        st.write("")

    if st.button("🔄 Translate", type="secondary"):
        translator_key = st.session_state['api_keys']['translator_key']
        translator_region = st.session_state['api_keys']['translator_region']

        if not translator_key or not translator_region:
            st.error("Please enter Azure Translator credentials in sidebar.")
        else:
            with st.spinner("Translating…"):
                url = f"https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&to={lang_options[selected_lang]}"
                headers = {
                    "Ocp-Apim-Subscription-Key": translator_key,
                    "Ocp-Apim-Subscription-Region": translator_region,
                    "Content-Type": "application/json",
                }
                body = [{"text": st.session_state.description_text}]
                res = requests.post(url, headers=headers, json=body)

            if res.status_code != 200:
                st.error(f"Translator error: {res.text}")
            else:
                translated = res.json()[0]["translations"][0]["text"]
                st.success(f"**{selected_lang}:** {translated}")

    # AI Chat Section
    st.divider()
    st.subheader("💬 Ask About This Place")
    st.caption("Llama AI (via Groq) can tell you about history, culture, food, best times to visit, and travel tips.")

    # Seed chat context
    if st.session_state.description_text and len(st.session_state.chat_history) == 0:
        tags = st.session_state.get('analyzed_tags', [])
        st.session_state.chat_history = [
            {
                "role": "user",
                "content": f'I\'m looking at a travel image: "{st.session_state.description_text}". Tags: {", ".join(tags)}. Give concise, helpful travel advice.'
            },
            {
                "role": "assistant",
                "content": f"Wonderful! I can see this is a travel photo showing: *{st.session_state.description_text}*. Ask me anything — history, best time to visit, local food, culture, tips, and more!"
            }
        ]

    display_history = st.session_state.chat_history[2:] if len(st.session_state.chat_history) >= 2 else st.session_state.chat_history
    for msg in display_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    question = st.chat_input("Ask about this place...")

    if question:
        groq_key = st.session_state['api_keys'].get('groq_key', '')
        if not groq_key:
            st.error("Please enter a Groq API key in sidebar (free at console.groq.com).")
        else:
            with st.chat_message("user"):
                st.write(question)
            st.session_state.chat_history.append({"role": "user", "content": question})

            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    try:
                        # Convert chat history to OpenAI format
                        messages = [
                            {"role": "system", "content": "You are a warm, knowledgeable travel guide. Provide concise, practical advice (2-4 sentences) about travel, culture, food, tips, customs, and history."}
                        ] + st.session_state.chat_history

                        client = openai.OpenAI(
                            api_key=groq_key,
                            base_url="https://api.groq.com/openai/v1"
                        )
                        response = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=messages,
                            max_tokens=1024,
                            temperature=0.7
                        )
                        reply = response.choices[0].message.content
                        st.write(reply)
                        st.session_state.chat_history.append({"role": "assistant", "content": reply})
                    except Exception as e:
                        st.error(f"AI error: {e}")

# ═══════════════════════════════════════════════════════════════
# PAGE: TRIP PLANNER
# ═══════════════════════════════════════════════════════════════
elif st.session_state['current_page'] == "🗺️ Trip Planner":
    st.markdown('<p class="main-header">🗺️ Trip Planner</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Plan, organize, and manage your travel itineraries</p>', unsafe_allow_html=True)
    st.divider()

    tab1, tab2, tab3 = st.tabs(["📅 Active Trips", "➕ Create New", "📝 Trip Details"])

    with tab1:
        trips = st.session_state['trips']

        if not trips:
            st.info("No trips yet. Create your first trip in the 'Create New' tab!")
        else:
            for i, trip in enumerate(trips):
                with st.expander(f"🎯 {trip['name']} — {trip.get('destination', 'No destination')}", expanded=False):
                    st.markdown(f"**📍 Destination:** {trip.get('destination', 'N/A')}")
                    st.markdown(f"**📅:** {trip.get('start_date', 'N/A')} → {trip.get('end_date', 'N/A')}")
                    st.markdown(f"**📌 Places:** {len(trip.get('places', []))} planned")

                    col_a, col_b, col_c = st.columns(3)
                    if col_a.button("✏️ Edit", key=f"edit_{i}"):
                        st.session_state['editing_trip'] = i
                        st.session_state['_settings_tab'] = 'trip_edit'
                    if col_b.button("🗑️ Delete", key=f"del_{i}"):
                        st.session_state['trips'].pop(i)
                        save_data('trips', st.session_state['trips'])
                        st.rerun()
                    if col_c.button("📋 Duplicate", key=f"dup_{i}"):
                        import copy
                        new_trip = copy.deepcopy(trip)
                        new_trip['id'] = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
                        new_trip['name'] = f"{trip['name']} (Copy)"
                        st.session_state['trips'].append(new_trip)
                        save_data('trips', st.session_state['trips'])
                        st.rerun()

    with tab2:
        st.markdown("### Create New Trip")

        trip_name = st.text_input("Trip Name", placeholder="e.g., Summer in Italy")
        destination = st.text_input("Destination", placeholder="e.g., Rome, Italy", key="new_dest")

        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", date.today())
        with date_col2:
            end_date = st.date_input("End Date", date.today())

        # Suggested places based on destination
        suggested_places = {
            "Italy": ["Colosseum", "Vatican Museums", "Trevi Fountain", "Pompeii", "Venice Canals"],
            "France": ["Eiffel Tower", "Louvre Museum", "Notre-Dame", "Versailles", "Mont Saint-Michel"],
            "Japan": ["Mt. Fuji", "Fushimi Inari", "Tokyo Tower", "Kinkaku-ji", "Senso-ji Temple"],
            "Spain": ["La Sagrada Familia", "Alhambra", "Prado Museum", "Park Güell", "Seville Cathedral"],
            "UK": ["Big Ben", "Tower of London", "British Museum", "Stonehenge", "Edinburgh Castle"],
            "USA": ["Statue of Liberty", "Grand Canyon", "Yellowstone", "Empire State Building", "Golden Gate"],
            "Thailand": ["Grand Palace", "Angkor Wat", "Chiang Mai Temples", "Phi Phi Islands", "Floating Markets"],
            "India": ["Taj Mahal", "Jaipur forts", "Kerala backwaters", "Varanasi Ghats", "Goa beaches"]
        }

        suggested = [v for k, v in suggested_places.items() if k.lower() in destination.lower()]
        if suggested:
            st.markdown("**💡 Suggested places:**")
            st.write(", ".join(suggested[0][:5]))

        notes = st.text_area("Trip Notes", placeholder="Any special plans or reminders...")

        if st.button("✅ Create Trip", type="primary", use_container_width=True):
            if not trip_name:
                st.error("Please enter a trip name")
            else:
                new_trip = {
                    'id': hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8],
                    'name': trip_name,
                    'destination': destination,
                    'start_date': str(start_date),
                    'end_date': str(end_date),
                    'places': [],
                    'notes': notes
                }
                st.session_state['trips'].append(new_trip)
                save_data('trips', st.session_state['trips'])
                st.success(f"Trip '{trip_name}' created! 🎉")
                st.rerun()

    with tab3:
        if 'editing_trip' in st.session_state and st.session_state['editing_trip'] is not None:
            idx = st.session_state['editing_trip']
            trip = st.session_state['trips'][idx]

            st.markdown(f"### Editing: {trip['name']}")

            trip['name'] = st.text_input("Trip Name", value=trip['name'])
            trip['destination'] = st.text_input("Destination", value=trip.get('destination', ''))
            trip['start_date'] = str(st.date_input("Start Date", datetime.strptime(trip['start_date'], '%Y-%m-%d').date()))
            trip['end_date'] = str(st.date_input("End Date", datetime.strptime(trip['end_date'], '%Y-%m-%d').date()))
            trip['notes'] = st.text_area("Notes", value=trip.get('notes', ''))

            st.markdown("#### 📌 Places to Visit")
            places = trip.get('places', [])

            new_place = st.text_input("Add a new place", placeholder="e.g., Eiffel Tower", key="new_place_input")
            if st.button("➕ Add Place", key="add_place_btn"):
                if new_place:
                    places.append({'name': new_place, 'visited': False, 'notes': ''})
                    trip['places'] = places
                    st.rerun()

            for j, place in enumerate(places):
                col1, col2, col3 = st.columns([3, 1, 1])
                place['visited'] = col1.checkbox(f"✅ {place['name']}", value=place.get('visited', False), key=f"place_{j}")
                place['notes'] = col2.text_input("Notes", value=place.get('notes', ''), placeholder="Tips...", key=f"notes_{j}")
                if col3.button("🗑️", key=f"del_place_{j}"):
                    places.pop(j)
                    st.rerun()

            trip['places'] = places

            if st.button("💾 Save Changes", type="primary"):
                st.session_state['trips'][idx] = trip
                save_data('trips', st.session_state['trips'])
                st.success("Trip updated!")
                st.session_state['editing_trip'] = None
                st.rerun()

            if st.button("❌ Cancel"):
                st.session_state['editing_trip'] = None
                st.rerun()
        else:
            st.info("Select a trip from 'Active Trips' tab to view details")

# ═══════════════════════════════════════════════════════════════
# PAGE: BUDGET TRACKER
# ═══════════════════════════════════════════════════════════════
elif st.session_state['current_page'] == "💰 Budget Tracker":
    st.markdown('<p class="main-header">💰 Budget Tracker</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Track expenses and manage your travel spending</p>', unsafe_allow_html=True)
    st.divider()

    expenses = st.session_state['expenses']

    # Summary cards
    total = sum(e.get('amount', 0) for e in expenses)
    today = date.today().isoformat()
    today_total = sum(e.get('amount', 0) for e in expenses if e.get('date', '') == today)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💵 Total Spent", f"${total:,.2f}")
    with col2:
        st.metric("📅 Today", f"${today_total:,.2f}")
    with col3:
        st.metric("📊 Transactions", len(expenses))

    st.divider()

    # Add expense
    with st.expander("➕ Add New Expense", expanded=True):
        exp_col1, exp_col2, exp_col3, exp_col4 = st.columns(4)

        with exp_col1:
            amount = st.number_input("Amount ($)", min_value=0.01, format="%.2f")
        with exp_col2:
            category = st.selectbox("Category", ["🍽️ Food", "🚕 Transport", "🏨 Accommodation",
                                                   "🎫 Tickets", "🛍️ Shopping", "💊 Health",
                                                   "📱 Communication", "☕ Drinks", "🎁 Gifts", "📦 Other"])
        with exp_col3:
            exp_date = st.date_input("Date", date.today())
        with exp_col4:
            trip_select = st.selectbox("Trip", ["General"] + [t['name'] for t in st.session_state['trips']])

        description = st.text_input("Description", placeholder="What did you spend on?")

        if st.button("Add Expense", type="primary"):
            new_expense = {
                'id': hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8],
                'amount': amount,
                'category': category,
                'description': description,
                'date': str(exp_date),
                'trip': trip_select
            }
            st.session_state['expenses'].append(new_expense)
            save_data('expenses', st.session_state['expenses'])
            st.success("Expense added!")
            st.rerun()

    st.divider()

    # Expense breakdown by category
    if expenses:
        st.markdown("### 📊 Spending by Category")
        categories = {}
        for e in expenses:
            cat = e.get('category', '📦 Other')
            categories[cat] = categories.get(cat, 0) + e.get('amount', 0)

        cat_cols = st.columns(len(categories)) if len(categories) <= 5 else st.columns(5)
        for i, (cat, amt) in enumerate(sorted(categories.items(), key=lambda x: -x[1])):
            with cat_cols[i % 5]:
                st.metric(cat, f"${amt:,.2f}")

        # Recent transactions
        st.markdown("### 📋 Recent Transactions")
        recent = sorted(expenses, key=lambda x: x.get('date', ''), reverse=True)[:10]

        for e in recent:
            exp_col1, exp_col2, exp_col3, exp_col4 = st.columns([3, 1, 1, 1])
            with exp_col1:
                st.markdown(f"**{e.get('description', 'No description')}**")
                st.caption(f"{e.get('category', '')} • {e.get('trip', 'General')}")
            with exp_col2:
                st.markdown(f"**${e.get('amount', 0):.2f}**")
            with exp_col3:
                st.caption(e.get('date', ''))
            with exp_col4:
                if st.button("🗑️", key=f"del_exp_{e['id']}"):
                    st.session_state['expenses'] = [x for x in expenses if x['id'] != e['id']]
                    save_data('expenses', st.session_state['expenses'])
                    st.rerun()

    # Export budget
    if expenses:
        st.divider()
        if st.button("📥 Export as CSV"):
            csv_content = "Date,Category,Description,Amount,Trip\n"
            for e in expenses:
                csv_content += f"{e.get('date','')},{e.get('category','')},{e.get('description','')},{e.get('amount',0)},{e.get('trip','')}\n"
            st.download_button("Download CSV", csv_content, "travel_expenses.csv", "text/csv")

# ═══════════════════════════════════════════════════════════════
# PAGE: PACKING LIST
# ═══════════════════════════════════════════════════════════════
elif st.session_state['current_page'] == "📋 Packing List":
    st.markdown('<p class="main-header">📋 Packing List</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Never forget essentials again</p>', unsafe_allow_html=True)
    st.divider()

    # Smart categories
    categories = {
        "👔 Clothing": ["T-shirts", "Pants", "Underwear", "Socks", "Sleepwear", "Jacket", "Swimwear"],
        "🧴 Toiletries": ["Toothbrush", "Toothpaste", "Shampoo", "Soap", "Deodorant", "Sunscreen", "Moisturizer"],
        "💊 Medicine": ["Prescription meds", "Pain relievers", "Motion sickness pills", "First aid kit"],
        "📱 Electronics": ["Phone charger", "Power bank", "Camera", "Headphones", "Adapter"],
        "🎫 Documents": ["Passport", "ID", "Tickets", "Hotel reservations", "Insurance", "Cash"],
        "💼 Miscellaneous": ["Backpack", "Day bag", "Reusable water bottle", "Snacks", "Book"]
    }

    items = st.session_state['packing_items']

    # Auto-suggest based on trips
    if st.session_state['trips']:
        st.markdown("#### 🚀 Quick Add from Trip Destinations")
        trip_destinations = [t.get('destination', '').lower() for t in st.session_state['trips']]

        suggest_col1, suggest_col2 = st.columns(2)
        with suggest_col1:
            if any('beach' in d or 'island' in d or 'coast' in d for d in trip_destinations):
                st.info("🏖️ Beach trip detected - suggested: Sunscreen, Swimsuit, Beach towel, Flip flops")
            if any('mountain' in d or 'hiking' in d for d in trip_destinations):
                st.info("🏔️ Mountain trip detected - suggested: Hiking boots, Rain jacket, Warm layers")
            if any('city' in d or 'europe' in d or 'museum' in d for d in trip_destinations):
                st.info("🏙️ City/Europe trip - suggested: Comfortable walking shoes, Power adapter, Day bag")

    # Add custom item
    add_col1, add_col2 = st.columns([3, 1])
    with add_col1:
        new_item = st.text_input("Add custom item", placeholder="Type an item name...")
    with add_col2:
        st.write("")  # spacing
        if st.button("➕ Add", type="primary"):
            if new_item:
                categories['💼 Miscellaneous'].append(new_item)
                st.rerun()

    st.divider()

    # Display by category
    for cat_name, cat_items in categories.items():
        with st.expander(f"{cat_name} ({len(cat_items)})", expanded=True):
            for item in cat_items:
                checked = item in items
                if st.checkbox(item, value=checked, key=f"item_{item}"):
                    if item not in items:
                        st.session_state['packing_items'].append(item)
                        save_data('packing_items', st.session_state['packing_items'])
                else:
                    if item in items:
                        st.session_state['packing_items'].remove(item)
                        save_data('packing_items', st.session_state['packing_items'])

    # Packing progress
    total_items = sum(len(v) for v in categories.values())
    packed = len([i for i in items if any(i in v for v in categories.values())])
    progress = packed / total_items if total_items > 0 else 0

    st.divider()
    st.progress(progress, text=f"📦 Packing progress: {packed}/{total_items} essentials packed")

    # Reset
    if st.button("🔄 Reset Packing List"):
        st.session_state['packing_items'] = []
        save_data('packing_items', st.session_state['packing_items'])
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# PAGE: WEATHER
# ═══════════════════════════════════════════════════════════════
elif st.session_state['current_page'] == "🌤️ Weather":
    st.markdown('<p class="main-header">🌤️ Weather</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Check weather conditions at your destination</p>', unsafe_allow_html=True)
    st.divider()

    # Popular destinations weather
    popular_cities = {
        "Paris, France": {"lat": 48.8566, "lon": 2.3522},
        "Tokyo, Japan": {"lat": 35.6762, "lon": 139.6503},
        "New York, USA": {"lat": 40.7128, "lon": -74.0060},
        "London, UK": {"lat": 51.5074, "lon": -0.1278},
        "Sydney, Australia": {"lat": -33.8688, "lon": 151.2093},
        "Dubai, UAE": {"lat": 25.2048, "lon": 55.2708},
        "Singapore": {"lat": 1.3521, "lon": 103.8198},
        "Bali, Indonesia": {"lat": -8.3405, "lon": 115.0920},
        "Rome, Italy": {"lat": 41.9028, "lon": 12.4964},
        "Barcelona, Spain": {"lat": 41.3851, "lon": 2.1734},
        "Mumbai, India": {"lat": 19.0760, "lon": 72.8777},
        "Bangkok, Thailand": {"lat": 13.7563, "lon": 100.5018}
    }

    # City selection
    city_options = ["Select a city..."] + list(popular_cities.keys())
    if st.session_state.get('selected_destination'):
        dest = st.session_state['selected_destination']
        if dest not in city_options:
            city_options.insert(1, dest)
            popular_cities[dest] = {"lat": 0, "lon": 0}

    selected_city = st.selectbox("🏙️ Select Destination", city_options)

    use_current = st.checkbox("📍 Use my trip destination", value=bool(st.session_state.get('selected_destination')))

    if use_current and st.session_state.get('selected_destination'):
        selected_city = st.session_state['selected_destination']
        if selected_city not in popular_cities:
            popular_cities[selected_city] = {"lat": 0, "lon": 0}

    if selected_city and selected_city != "Select a city...":
        coords = popular_cities[selected_city]

        with st.spinner("Fetching weather..."):
            try:
                # Open-Meteo API (free, no key needed)
                weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m&timezone=auto"
                weather_resp = requests.get(weather_url, timeout=10)
                weather_data = weather_resp.json()

                if weather_resp.status_code == 200 and weather_data.get('current'):
                    current = weather_data['current']

                    # Weather code to description
                    weather_codes = {
                        0: ("Clear sky", "☀️"),
                        1: ("Mainly clear", "🌤️"),
                        2: ("Partly cloudy", "⛅"),
                        3: ("Overcast", "☁️"),
                        45: ("Foggy", "🌫️"),
                        48: ("Depositing rime fog", "🌫️"),
                        51: ("Light drizzle", "🌧️"),
                        53: ("Moderate drizzle", "🌧️"),
                        55: ("Dense drizzle", "🌧️"),
                        61: ("Slight rain", "🌧️"),
                        63: ("Moderate rain", "🌧️"),
                        65: ("Heavy rain", "🌧️"),
                        71: ("Slight snow", "🌨️"),
                        73: ("Moderate snow", "🌨️"),
                        75: ("Heavy snow", "🌨️"),
                        80: ("Slight rain showers", "🌦️"),
                        81: ("Moderate rain showers", "🌦️"),
                        82: ("Violent rain showers", "⛈️"),
                        95: ("Thunderstorm", "⛈️")
                    }

                    code = current.get('weather_code', 0)
                    desc, icon = weather_codes.get(code, ("Unknown", "❓"))

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("🌡️ Temperature", f"{current.get('temperature_2m', 0):.1f}°C",
                                  f"Feels like {current.get('apparent_temperature', 0):.1f}°C")
                    with col2:
                        st.metric("💧 Humidity", f"{current.get('relative_humidity_2m', 0)}%")
                    with col3:
                        st.metric("💨 Wind", f"{current.get('wind_speed_10m', 0)} km/h")
                    with col4:
                        st.metric(f"{icon} Condition", desc)

                    # Timezone
                    tz = weather_data.get('timezone', 'Unknown')
                    local_time = datetime.now(pytz.timezone(tz)).strftime('%A, %B %d, %Y %I:%M %p')
                    st.info(f"📍 {selected_city} | 🕐 Local time: {local_time}")

                    # Clothing recommendations
                    temp = current.get('temperature_2m', 20)
                    st.markdown("#### 👔 Packing Recommendation")
                    if temp < 10:
                        st.warning("🥶 Cold! Pack warm layers, heavy jacket, gloves, and scarf")
                    elif temp < 20:
                        st.info("🌤️ Mild! Light jacket and layers recommended")
                    elif temp < 30:
                        st.success("☀️ Warm! T-shirts and comfortable clothing")
                    else:
                        st.error("🔥 Hot! Light breathable clothes, sunscreen, and stay hydrated")

                    # Save destination for trip
                    if st.button(f"🗺️ Add {selected_city} to trip"):
                        st.session_state['selected_destination'] = selected_city
                        st.success(f"{selected_city} saved!")

            except Exception as e:
                st.error(f"Could not fetch weather: {e}")

# ═══════════════════════════════════════════════════════════════
# PAGE: CURRENCY CONVERTER
# ═══════════════════════════════════════════════════════════════
elif st.session_state['current_page'] == "💱 Currency":
    st.markdown('<p class="main-header">💱 Currency Converter</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time exchange rates for your travels</p>', unsafe_allow_html=True)
    st.divider()

    currencies = {
        "USD": "🇺🇸 US Dollar", "EUR": "🇪🇺 Euro", "GBP": "🇬🇧 British Pound",
        "JPY": "🇯🇵 Japanese Yen", "AUD": "🇦🇺 Australian Dollar", "CAD": "🇨🇦 Canadian Dollar",
        "CHF": "🇨🇭 Swiss Franc", "CNY": "🇨🇳 Chinese Yuan", "INR": "🇮🇳 Indian Rupee",
        "MXN": "🇲🇽 Mexican Peso", "BRL": "🇧🇷 Brazilian Real", "KRW": "🇰🇷 South Korean Won",
        "SGD": "🇸🇬 Singapore Dollar", "HKD": "🇭🇰 Hong Kong Dollar", "THB": "🇹🇭 Thai Baht",
        "AED": "🇦🇪 UAE Dirham", "NZD": "🇳🇿 New Zealand Dollar", "SEK": "🇸🇪 Swedish Krona",
        "NOK": "🇳🇴 Norwegian Krone", "DKK": "🇩🇰 Danish Krone", "ZAR": "🇿🇦 South African Rand",
        "RUB": "🇷🇺 Russian Ruble", "TRY": "🇹🇷 Turkish Lira", "PHP": "🇵🇭 Philippine Peso",
        "IDR": "🇮🇩 Indonesian Rupiah", "MYR": "🇲🇾 Malaysian Ringgit", "VND": "🇻🇳 Vietnamese Dong"
    }

    col1, col2, col3 = st.columns([2, 0.5, 2])

    with col1:
        st.session_state['currency_from'] = st.selectbox("From", list(currencies.keys()), index=0, format_func=lambda x: currencies[x])
        st.session_state['currency_amount'] = st.number_input("Amount", min_value=1.0, value=100.0, format="%.2f")

    with col3:
        st.session_state['currency_to'] = st.selectbox("To", list(currencies.keys()), index=1, format_func=lambda x: currencies[x])

    # Swap button
    with col2:
        st.write("")
        st.write("")
        if st.button("⇆ Swap"):
            st.session_state['currency_from'], st.session_state['currency_to'] = \
                st.session_state['currency_to'], st.session_state['currency_from']

    st.divider()

    # Popular presets
    st.markdown("#### ⚡ Quick Convert")
    presets = [("100 USD → EUR", "USD", "EUR", 100), ("1000 EUR → USD", "EUR", "USD", 1000),
               ("10000 JPY → USD", "JPY", "USD", 10000), ("1000 GBP → EUR", "GBP", "EUR", 1000)]

    for label, frm, to, amt in presets:
        if st.button(label):
            st.session_state['currency_from'] = frm
            st.session_state['currency_to'] = to
            st.session_state['currency_amount'] = amt
            st.rerun()

    # Fetch conversion
    with st.spinner("Fetching exchange rates..."):
        try:
            # Using exchangerate-api (free tier)
            from_code = st.session_state['currency_from']
            to_code = st.session_state['currency_to']
            amount = st.session_state['currency_amount']

            # Open Exchange Rates API alternative (exchangerate-api.com)
            response = requests.get(f"https://api.exchangerate-api.com/v4/latest/{from_code}", timeout=10)

            if response.status_code == 200:
                data = response.json()
                rate = data['rates'].get(to_code, 0)
                result = amount * rate

                st.success(f"💱 **{amount:,.2f} {from_code}** = **{result:,.2f} {to_code}**")
                st.caption(f"Exchange rate: 1 {from_code} = {rate:,.4f} {to_code} | Source: Exchange Rate API")
            else:
                st.error("Could not fetch exchange rates")

        except Exception as e:
            st.error(f"Error: {e}")

# ═══════════════════════════════════════════════════════════════
# PAGE: EMERGENCY INFO
# ═══════════════════════════════════════════════════════════════
elif st.session_state['current_page'] == "🆘 Emergency Info":
    st.markdown('<p class="main-header">🆘 Emergency Information</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Important contacts and safety info for your travels</p>', unsafe_allow_html=True)
    st.divider()

    countries = {
        "France": {"police": "17", "ambulance": "15", "fire": "18", " embassy": "+33 1 43 12 22 22"},
        "Italy": {"police": "113", "ambulance": "118", "fire": "115", "embassy": "+39 06 4224 0000"},
        "Spain": {"police": "091", "ambulance": "061", "fire": "080", "embassy": "+34 91 587 2200"},
        "Germany": {"police": "110", "ambulance": "112", "fire": "112", "embassy": "+49 30 83050"},
        "UK": {"police": "999", "ambulance": "999", "fire": "999", "embassy": "+44 20 7930 1234"},
        "USA": {"police": "911", "ambulance": "911", "fire": "911", "embassy": "+1 202 501 4444"},
        "Japan": {"police": "110", "ambulance": "119", "fire": "119", "embassy": "+81 3 3224 5000"},
        "Australia": {"police": "000", "ambulance": "000", "fire": "000", "embassy": "+61 2 6216 5600"},
        "Thailand": {"police": "191", "ambulance": "1669", "fire": "199", "embassy": "+66 2 287 3000"},
        "India": {"police": "100", "ambulance": "102", "fire": "101", "embassy": "+91 11 2688 2100"},
        "Singapore": {"police": "999", "ambulance": "995", "fire": "995", "embassy": "+65 6476 9121"},
        "UAE": {"police": "999", "ambulance": "998", "fire": "997", "embassy": "+971 4 394 6666"},
        "Mexico": {"police": "911", "ambulance": "911", "fire": "911", "embassy": "+52 55 5093 3200"},
        "Brazil": {"police": "190", "ambulance": "192", "fire": "193", "embassy": "+55 61 3312 7000"},
        "Netherlands": {"police": "112", "ambulance": "112", "fire": "112", "embassy": "+31 70 427 0427"}
    }

    country = st.selectbox("🌍 Select Country", list(countries.keys()),
                           index=countries.keys().index(st.session_state.get('emergency_country', 'France')) if st.session_state.get('emergency_country') in countries else 0)

    st.session_state['emergency_country'] = country

    if country:
        info = countries[country]

        st.markdown(f"### 🚨 Emergency Numbers - {country}")

        num_col1, num_col2, num_col3 = st.columns(3)
        with num_col1:
            st.markdown('<div class="warning-card">🚔 <strong>Police</strong><br><span style="font-size:2rem">{}</span></div>'.format(info['police']), unsafe_allow_html=True)
        with num_col2:
            st.markdown('<div class="warning-card">🚑 <strong>Ambulance</strong><br><span style="font-size:2rem">{}</span></div>'.format(info['ambulance']), unsafe_allow_html=True)
        with num_col3:
            st.markdown('<div class="warning-card">🔥 <strong>Fire</strong><br><span style="font-size:2rem">{}</span></div>'.format(info['fire']), unsafe_allow_html=True)

        st.markdown(f"#### 🏛️ Embassy/Consulate")
        st.info(f"**{country} Embassy/Consulate:** {info.get('embassy', 'N/A')}")

        # General tips
        st.divider()
        st.markdown("#### ✅ Travel Safety Tips")
        tips = [
            "📸 Keep copies of your passport and important documents in cloud storage",
            "💳 Notify your bank of travel dates to avoid card blocks",
            "🏨 Keep hotel address in local language on your phone",
            "🆘 Register with your country's travel notification system",
            "💊 Carry prescription medications in original packaging",
            "📱 Save emergency numbers offline (screenshot them)",
            "👥 Share itinerary with family/friends back home"
        ]
        for tip in tips:
            st.markdown(tip)

# ═══════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ═══════════════════════════════════════════════════════════════
elif st.session_state['current_page'] == "⚙️ Settings":
    st.markdown('<p class="main-header">⚙️ Settings</p>', unsafe_allow_html=True)
    st.divider()

    st.markdown("### 🔑 API Configuration")

    with st.expander("Azure Vision API", expanded=True):
        st.session_state['api_keys']['vision_key'] = st.text_input(
            "Subscription Key", value=st.session_state['api_keys'].get('vision_key',''), type="password", key="s_vision_key"
        )
        st.session_state['api_keys']['vision_endpoint'] = st.text_input(
            "Endpoint URL", value=st.session_state['api_keys'].get('vision_endpoint',''),
            placeholder="https://your-resource.cognitiveservices.azure.com/", key="s_vision_ep"
        )
        st.caption("Used for: Image analysis, object detection, scene understanding")

    with st.expander("Azure Translator API"):
        st.session_state['api_keys']['translator_key'] = st.text_input(
            "Subscription Key", value=st.session_state['api_keys'].get('translator_key',''), type="password", key="s_trans_key"
        )
        st.session_state['api_keys']['translator_region'] = st.text_input(
            "Region", value=st.session_state['api_keys'].get('translator_region',''),
            placeholder="e.g. centralindia", key="s_trans_region"
        )
        st.caption("Used for: Translating text to multiple languages")

    with st.expander("Groq API (Free - Llama AI)"):
        st.session_state['api_keys']['groq_key'] = st.text_input(
            "API Key (free at console.groq.com)", value=st.session_state['api_keys'].get('groq_key',''), type="password", key="s_groq"
        )
        st.caption("Used for: Free AI-powered travel assistant chat (Llama 3.1 8B)")

    st.divider()

    # Data management
    st.markdown("### 💾 Data Management")

    data_col1, data_col2 = st.columns(2)

    with data_col1:
        st.markdown("**Your Data:**")
        st.write(f"📅 Trips: {len(st.session_state['trips'])}")
        st.write(f"💰 Expenses: {len(st.session_state['expenses'])}")
        st.write(f"📋 Packing items: {len(st.session_state['packing_items'])}")

    with data_col2:
        if st.button("🗑️ Clear All Data", type="secondary"):
            st.session_state['trips'] = []
            st.session_state['expenses'] = []
            st.session_state['packing_items'] = []
            for name in ['trips', 'expenses', 'packing_items']:
                save_data(name, [])
            st.warning("All data cleared!")

    st.divider()
    st.markdown("### ℹ️ About")
    st.caption("Wanderlust Pro v2.0 — Your AI-powered travel companion")
    st.caption("Built with Streamlit, Azure AI, and Groq (Free Llama AI)")
