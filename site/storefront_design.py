"""Editorial storefront sections; public copy is available in RU, HY and EN."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARTICLES = json.loads((ROOT / "editorial.json").read_text(encoding="utf-8"))
TRANSLATIONS = json.loads((ROOT / "storefront-translations.json").read_text(encoding="utf-8"))
ROOM_IMAGES = {"living-room":"yerevan-layers","bedroom":"gyumri-bedroom","kitchen":"kitchen-zones","workspace":"home-office","outdoors":"dilijan-terrace"}

def t(ru, hy=None, en=None):
    if hy is not None:
        TRANSLATIONS[ru] = [hy,en]
    return html.escape(ru)

def text(value):
    return t(*value)

def footer_intro():
    return '<p>'+t("Люсар — свет для дома, встреч и повседневных открытий. От выразительного подвеса до тихого света у кровати: выбирайте свой характер освещения.",
      "Լյուսար՝ լույս տան, հանդիպումների և առօրյա բացահայտումների համար։ Արտահայտիչ կախովի լուսատուից մինչև մահճակալի մեղմ լույս․ ընտրեք ձեր լուսավորությունը։",
      "Lusar is light for home, gathering and everyday discovery. From a statement pendant to a quiet bedside glow: find your own way to light a room.")+'</p>'

def footer_stores():
    return ('<section class="footer-stores" aria-label="'+t("Наши магазины","Մեր խանութները","Our stores")+'"><div class="stores-invitation"><span class="eyebrow">'+t("Будем рады встрече","Սպասում ենք ձեզ","Come and see us")+'</span><h2>'+t("Увидеть свет вживую","Տեսեք լույսը իրականում","Experience the light")+'</h2><p>'+t("Ереван · ежедневно 09:30–19:00","Երևան · ամեն օր 09:30–19:00","Yerevan · daily 09:30–19:00")+'</p><a class="footer-phone" href="tel:+37477123451">+374 (77) 12-34-51</a></div><a class="store-location" href="/stores/yerevan-arshakunyats"><span class="store-index" aria-hidden="true">01</span><div><strong>'+t("Аршакуняц, 210/1","Արշակունյաց 210/1","210/1 Arshakunyats")+'</strong><p>'+t("Ярмарка «Еранкюни»","«Եռանկյունի» տոնավաճառ","Yerankyuni market")+'</p></div><span class="location-dot" aria-hidden="true"></span></a><a class="store-location" href="/stores/yerevan-smbat-zoravar"><span class="store-index" aria-hidden="true">02</span><div><strong>'+t("Смбата Зоравара, 11/3","Սմբատ Զորավարի 11/3","11/3 Smbat Zoravar")+'</strong><p>'+t("Павильон D50","Տաղավար D50","Pavilion D50")+'</p></div><span class="location-dot" aria-hidden="true"></span></a></section>')

def home_service(icon):
    rows=[
      ("lamp",["Под вашу задачу","Ձեր խնդրի համար","For the way you live"],["Общий свет, акцент или уютный уголок — начните с того, что важно вам.","Ընդհանուր լույս, շեշտադրում կամ հարմարավետ անկյուն․ սկսեք ձեզ համար կարևորից։","General light, an accent or a quiet corner: start with what matters to you."]),
      ("spark",["Примерка до решения","Փորձեք նախքան ընտրելը","See it before deciding"],["Посмотрите на выбранный светильник в своей комнате с Lusar AI.","Տեսեք ընտրված լուսատուն ձեր սենյակում՝ Lusar AI-ով։","Preview your chosen fixture in your room with Lusar AI."]),
      ("account",["Менеджер на связи","Մենեջերը կապի մեջ է","A person to help"],["Оформите заявку без онлайн-оплаты. Детали и наличие подтвердит менеджер.","Ուղարկեք հայտ՝ առանց առցանց վճարման։ Մանրամասները և առկայությունը կհաստատի մենեջերը։","Send a request without paying online. A manager confirms availability and details."])]
    return '<section class="home-service" aria-label="Выбор освещения">'+''.join('<article>'+icon(i)+'<h2>'+text(h)+'</h2><p>'+text(p)+'</p></article>' for i,h,p in rows)+'</section>'

def article_card(item):
    loading = "eager" if item in ARTICLES[:3] else "lazy"
    return ('<a class="journal-card" href="/journal/'+item["slug"]+'"><span class="journal-card-media"><img src="/editorial/'+item["slug"]+'.webp" width="960" height="540" loading="'+loading+'" decoding="async" alt="'+text(item["title"])+
      '"></span><div class="journal-card-copy"><div class="journal-meta"><span>'+text(item["place"])+'</span><span>'+
      t("3 минуты","3 րոպե","3 min")+'</span></div><h2>'+text(item["title"])+'</h2><p>'+text(item["intro"])+'</p></div></a>')

def home_editorial():
    return '<section class="home-editorial"><div class="section-heading"><h2>'+t("О свете и пространстве","Լույսի և տարածքի մասին","Light and space")+'</h2><a class="direction-link" href="/journal">'+t("Все статьи","Բոլոր հոդվածները","All articles")+'</a></div><ul class="journal-grid">'+''.join('<li>'+article_card(item)+'</li>' for item in ARTICLES[:2])+'</ul></section>'

ROOM_PLANS = {
 "living-room":[
   ["Начните с вечернего маршрута: диван, кресло для чтения, стол. Для каждой задачи нужен удобный источник, а не одна яркая люстра.",
    "Սկսեք երեկոյան զբաղմունքներից՝ բազմոց, ընթերցանության բազկաթոռ, սեղան։ Յուրաքանչյուրի համար նախատեսեք հարմար աղբյուր, ոչ միայն մեկ պայծառ ջահ։",
    "Map your evening: sofa, reading chair and table. Give each activity a useful light rather than relying on one bright chandelier."],
   ["Добавьте бра сбоку от дивана и отдельный свет над столом. Раздельное включение помогает сохранить уют, когда часть комнаты не используется.",
    "Բազմոցի կողքին ավելացրեք պատի լուսատու, իսկ սեղանի վերևում՝ առանձին լույս։ Առանձին միացումը պահպանում է հարմարավետությունը։",
    "Add a wall light beside the sofa and separate lighting over the table. Independent switches keep unused areas calm."],
   ["Сверьте высоту потолка и габариты мебели. На фото для примерки должны быть видны потолок, стены и место установки.",
    "Ստուգեք առաստաղի բարձրությունն ու կահույքի չափերը։ Փորձարկման լուսանկարում թող երևան առաստաղը, պատերը և տեղադրման վայրը։",
    "Check ceiling height and furniture dimensions. Your preview photo should show the ceiling, walls and mounting position."]],
 "bedroom":[
   ["Продумайте два сценария: собраться утром и спокойно завершить день. Яркий общий свет и мягкий прикроватный должны включаться отдельно.",
    "Մտածեք երկու սցենար՝ պատրաստվել առավոտյան և հանգստանալ երեկոյան։ Ընդհանուր և մահճակալի լույսերը պետք է միանան առանձին։",
    "Plan for getting ready and winding down. General lighting and gentle bedside light should have separate controls."],
   ["Для чтения важнее направление света, чем размер плафона. Проверьте положение бра относительно подушки и возможность выключить его из кровати.",
    "Ընթերցանության համար լույսի ուղղությունն ավելի կարևոր է, քան լուսամփոփի չափը։ Ստուգեք դիրքը բարձի նկատմամբ և անկողնուց անջատելու հնարավորությունը։",
    "Reading depends on light direction more than shade size. Check the position beside your pillow and whether you can switch it off from bed."],
   ["Если рассматриваете диммирование, уточните совместимость светильника, лампы и регулятора. Надпись LED сама по себе этого не гарантирует.",
    "Պայծառության կարգավորման համար ստուգեք լուսատուի, լամպի և կարգավորիչի համատեղելիությունը։ Միայն LED նշումը բավարար չէ։",
    "For dimming, check compatibility between fixture, lamp and dimmer. The LED label alone does not guarantee it."]],
 "kitchen":[
   ["Разделите рабочую поверхность и обеденный стол. Красивый подвес над столом не заменяет свет там, где вы режете и готовите.",
    "Առանձնացրեք աշխատանքային մակերեսն ու ճաշասեղանը։ Սեղանի գեղեցիկ կախովի լուսատուն չի փոխարինում պատրաստելու տեղի լույսին։",
    "Separate worktops from dining. A beautiful dining pendant does not replace light where you chop and prepare food."],
   ["Расположите свет так, чтобы вы не закрывали его собой. Для длинного стола сравните линейный подвес и несколько компактных моделей.",
    "Լույսը տեղադրեք այնպես, որ մարմնով չփակեք այն։ Երկար սեղանի համար համեմատեք գծային և մի քանի փոքր կախովի լուսատուներ։",
    "Position light so your body does not block it. Compare a linear pendant with several smaller fixtures for a long table."],
   ["Измерьте стол, остров и проходы. Длину подвеса выбирайте с учётом обзора, открывания шкафов и рекомендаций производителя.",
    "Չափեք սեղանը, կղզին և անցումները։ Կախոցի երկարությունն ընտրեք՝ հաշվի առնելով տեսադաշտը, պահարաններն ու արտադրողի ցուցումները։",
    "Measure the table, island and circulation routes. Set suspension length around sightlines, cupboards and manufacturer instructions."]],
 "workspace":[
   ["Сначала определите место экрана и направление дневного света. Блики в мониторе нельзя надёжно исправить просто более яркой лампой.",
    "Նախ որոշեք էկրանի տեղն ու ցերեկային լույսի ուղղությունը։ Մոնիտորի փայլերը միայն ավելի պայծառ լամպով չեն լուծվում։",
    "Start with screen position and daylight direction. A brighter lamp alone will not solve monitor glare."],
   ["Нужен свет на столе и спокойный фон вокруг. Направляемая лампа позволяет осветить документы, не направляя источник в глаза.",
    "Պետք են լուսավորված սեղան և հանգիստ ֆոն։ Ուղղվող լամպով լուսավորեք թղթերը՝ առանց աղբյուրը աչքերին ուղղելու։",
    "Light the desk and keep the surrounding room comfortable. An adjustable lamp can illuminate papers without shining into your eyes."],
   ["Проверьте свет сидя за столом, включая видеозвонок. Уточните мерцание и возможность регулировки по документации конкретной модели.",
    "Լույսը ստուգեք նստած՝ նաև տեսազանգի ընթացքում։ Թարթման և կարգավորման տվյալները ճշտեք կոնկրետ մոդելի փաստաթղթերով։",
    "Test lighting while seated, including a video call. Check flicker and adjustment specifications for the actual model."]],
 "outdoors":[
   ["Выделите вход, ступени и место отдыха. Для террасы в Дилижане и открытого балкона в Ереване условия установки будут разными.",
    "Առանձնացրեք մուտքը, աստիճանները և հանգստի տեղը։ Դիլիջանի տեռասի և Երևանի բաց պատշգամբի պայմանները տարբեր են։",
    "Identify entrances, steps and seating. A Dilijan terrace and an exposed Yerevan balcony present different installation conditions."],
   ["Выбирайте модель по защите от воды и пыли, температурному диапазону и материалам. Уличный вид корпуса не подтверждает пригодность для улицы.",
    "Ընտրեք ըստ ջրի ու փոշու պաշտպանության, ջերմաստիճանի միջակայքի և նյութերի։ Արտաքին տեսքը չի հաստատում բացօթյա կիրառելիությունը։",
    "Check ingress protection, temperature range and materials. An outdoor-looking housing does not prove outdoor suitability."],
   ["Покажите электрику место монтажа и условия воздействия дождя. Направляйте свет вниз и не в окна соседей; подключение поручите специалисту.",
    "Էլեկտրիկին ցույց տվեք տեղադրումն ու անձրևի ազդեցությունը։ Լույսն ուղղեք ներքև, ոչ հարևանների պատուհաններին։ Միացումը վստահեք մասնագետին։",
    "Show the mounting position and rain exposure to an electrician. Aim light down, away from neighbours' windows, and use qualified installation."]]}

def render_rooms(write, rooms, category_cards, product_grid, products, icon):
    title=t("Свет для каждой комнаты","Լույս՝ յուրաքանչյուր սենյակի համար","Light for every room")
    intro=t("Начните с того, как вы живёте в пространстве. Подскажем, какие задачи разделить, что измерить и какие светильники посмотреть.",
      "Սկսեք նրանից, թե ինչպես եք օգտագործում տարածքը։ Կօգնենք առանձնացնել խնդիրները, չափել կարևոր մասերն ու ընտրել լուսատուները։",
      "Start with how you use a space. Find the lighting tasks to separate, the dimensions to measure and fixtures to explore.")
    cards=[]
    for key,(name,tip,related) in rooms.items():
        cards.append('<a class="room-card" href="/rooms/'+key+'"><img src="/editorial/'+ROOM_IMAGES[key]+'.webp" width="960" height="540" loading="lazy" alt=""><div><h2>'+html.escape(name)+'</h2><p>'+html.escape(tip)+'</p><span class="room-card-meta">'+icon(ROOM_ICON[key])+t("Сценарий и подборка","Սցենար և ընտրանի","Plan and collection")+'</span></div></a>')
        plan='<div class="room-plan">'+''.join('<article><span class="step-number">0'+str(i)+'</span><h2>'+text(h)+'</h2><p>'+text(p)+'</p></article>' for i,(h,p) in enumerate(zip([
          ["Задача","Խնդիրը","The task"],["Сценарий","Սցենարը","The plan"],["Перед покупкой","Գնելուց առաջ","Before ordering"]],ROOM_PLANS[key]),1))+'</div>'
        write("rooms/"+key,name,'<section class="room-detail-hero"><img src="/editorial/'+ROOM_IMAGES[key]+'.webp" width="960" height="540" alt=""><div><a href="/rooms">'+t("Все комнаты","Բոլոր սենյակները","All rooms")+'</a><h1>'+html.escape(name)+'</h1><p>'+html.escape(tip)+'</p><a class="ai-action" href="/ai">'+icon("spark")+'Lusar AI · '+t("Примерить свет","Փորձել լուսավորությունը","Preview the lighting")+'</a></div></section>'+plan+
          '<div class="section-heading"><h2>'+t("Подходящие категории","Համապատասխան կատեգորիաներ","Explore these categories")+'</h2></div>'+category_cards([key for key in related])+
          '<div class="section-heading"><h2>'+t("Светильники для вашего сценария","Լուսատուներ ձեր սցենարի համար","Fixtures for your plan")+'</h2></div>'+product_grid([item for item in products if item["categoryId"] in related][:6]),description=tip)
    write("rooms","Подобрать свет по комнате",'<header class="editorial-heading"><div><span class="eyebrow">LUSAR · '+t("По комнатам","Ըստ սենյակի","By room")+'</span><h1>'+title+'</h1><p>'+intro+'</p></div><a class="ai-action" href="/ai">'+icon("spark")+'Lusar AI</a></header><div class="room-gallery">'+''.join(cards)+'</div>',description="Практические сценарии освещения гостиной, спальни, кухни, рабочего места и террасы в Армении.")

ROOM_ICON={"living-room":"sofa","bedroom":"bed","kitchen":"dining","workspace":"desk","outdoors":"outdoor"}

def render_journal(write):
    body='<header class="editorial-heading"><div><span class="eyebrow">LUSAR · '+t("Журнал о свете","Լուսավորության ամսագիր","Lighting journal")+'</span><h1>'+t("Свет, с которым удобно жить","Լույս, որի հետ հարմար է ապրել","Light that works for your life")+'</h1><p>'+t("Как выбрать светильник, продумать свет в комнате и сделать повседневные дела комфортнее.","Ինչպես ընտրել լուսատուն, պլանավորել սենյակի լույսը և առօրյան դարձնել հարմարավետ։","Ideas for choosing fixtures, planning a room’s lighting and making everyday life more comfortable.")+'</p></div></header>'
    body+='<nav class="journal-filters" aria-label="Темы статей">'+''.join('<button type="button" data-journal-filter="'+key+'" aria-pressed="'+str(key=="all").lower()+'">'+text(label)+'</button>' for key,label in [("all",["Все статьи","Բոլոր հոդվածները","All articles"]),("apartment",["Квартира","Բնակարան","Apartment"]),("outside",["Дом и улица","Տուն և բացօթյա","House and outdoors"]),("details",["Детали света","Լույսի մանրամասները","Lighting details"])])+'</nav><ul class="journal-grid">'+''.join('<li data-journal-category="'+item["category"]+'">'+article_card(item)+'</li>' for item in ARTICLES)+'</ul>'
    write("journal","Статьи",body,description="Практические статьи об освещении: выбор светильников, уютный дом, рабочий свет и детали интерьера.")
    for item in ARTICLES:
        title=text(item["title"])
        content='<a class="direction-link" href="/journal">'+t("Все статьи","Բոլոր հոդվածները","All articles")+'</a><header class="editorial-heading"><div><span class="eyebrow">'+text(item["place"])+' · '+t("Практика света","Լուսավորության ուղեցույց","Practical lighting")+'</span><h1>'+title+'</h1><p>'+text(item["intro"])+'</p></div></header><figure class="article-cover"><img src="/editorial/'+item["slug"]+'.webp" width="1672" height="941" fetchpriority="high" alt="'+title+'"><figcaption>'+t("Редакционная иллюстрация, созданная ИИ.","Խմբագրական պատկեր՝ ստեղծված ԱԲ-ով։","AI-generated editorial illustration.")+'</figcaption></figure><div class="article-layout"><article class="article-body">'
        for heading,paragraph in zip(item["headings"],item["body"]):
            content+='<h2>'+text(heading)+'</h2><p>'+text(paragraph)+'</p>'
        content+='<p class="reading-tip">'+text(item["check"])+'</p>'
        if item.get("sources"):
            content+='<div class="article-sources"><span>'+t("Источники по теме","Թեմայի աղբյուրներ","Further reading")+'</span><br>'+''.join('<a href="'+url+'" rel="noopener">'+html.escape(label)+'</a>' for label,url in item["sources"])+'</div>'
        content+='</article><aside class="article-aside"><h2>'+t("От идеи к своему свету","Գաղափարից՝ ձեր լուսավորությանը","From idea to your own lighting")+'</h2><p>'+t("Сохраните размеры комнаты, выберите модели и оцените их на своём фото. Наличие и детали установки уточните у менеджера.","Գրեք սենյակի չափերը, ընտրեք մոդելները և գնահատեք ձեր լուսանկարում։ Առկայությունն ու տեղադրման մանրամասները ճշտեք մենեջերի հետ։","Note your room dimensions, choose fixtures and preview them on your photo. Ask a manager about availability and installation details.")+'</p><a class="button-link" href="/catalog">'+t("Открыть каталог","Բացել կատալոգը","Explore catalogue")+'</a><p><a class="ai-action" href="/ai">✧ Lusar AI</a></p><a href="tel:+37477123451">+374 (77) 12-34-51</a></aside></div>'
        write("journal/"+item["slug"],item["title"][0],content,description=item["intro"][0],image="https://lusar.am/editorial/"+item["slug"]+".webp",
          structured_data={"@context":"https://schema.org","@type":"Article","headline":item["title"][0],"description":item["intro"][0],"image":"https://lusar.am/editorial/"+item["slug"]+".webp","author":{"@type":"Organization","name":"LUSAR"},"publisher":{"@type":"Organization","name":"LUSAR"},"inLanguage":"ru","mainEntityOfPage":"https://lusar.am/journal/"+item["slug"]})

def search_entries():
    return [{"name":item["title"][0],"path":"/journal/"+item["slug"],"sku":"","keywords":" ".join(item["title"]+item["place"]+item["intro"])} for item in ARTICLES]

def offers(icon):
    return '<header class="editorial-heading"><div><span class="eyebrow">LUSAR · '+t("Особые поводы","Հատուկ առիթներ","Special occasions")+'</span><h1>'+t("Больше света. Приятнее повод.","Ավելի շատ լույս։ Հաճելի առիթ։","More light. A little more to celebrate.")+'</h1><p>'+t("Предложения с понятными условиями. Итоговую сумму и наличие подтвердит менеджер до оплаты.","Առաջարկներ՝ պարզ պայմաններով։ Վերջնական գումարն ու առկայությունը մենեջերը կհաստատի վճարումից առաջ։","Clear offers with clear terms. A manager confirms the final total and availability before payment.")+'</p></div></header><div class="offer-grid"><article class="offer-card"><span class="eyebrow">'+t("Первое знакомство","Առաջին ծանոթությունը","A first hello")+'</span><div class="offer-value">10%</div><h2>'+t("На первый заказ","Առաջին պատվերի համար","Off your first order")+'</h2><p>'+t("Зарегистрируйтесь и выберите скидку на первый заказ при оформлении. Доступна всем зарегистрированным клиентам без выполненных заказов. Отмена заказа сохраняет право на предложение.","Գրանցվեք և ձևակերպելիս ընտրեք առաջին պատվերի զեղչը։ Հասանելի է ավարտված պատվեր չունեցող բոլոր գրանցված գնորդներին։ Չեղարկման դեպքում իրավունքը պահպանվում է։","Register and select the first-order discount at checkout. Available to registered customers with no completed orders. A cancelled order preserves eligibility.")+'</p><p>'+t("Без минимальной суммы. Применяется отдельно от промокода и скидки кабинета.","Առանց նվազագույն գումարի։ Կիրառվում է պրոմոկոդից և անձնական զեղչից առանձին։","No minimum spend. Used separately from promo codes and account discounts.")+'</p><a class="button-link" href="/account/register">'+t("Зарегистрироваться","Գրանցվել","Register")+'</a></article><article class="offer-card"><span class="eyebrow">'+t("Ваш день","Ձեր օրը","Your day")+'</span><div class="offer-value">10%</div><h2>'+t("С днём рождения!","Ծնունդդ շնորհավոր։","Happy birthday!")+'</h2><p>'+t("В день рождения введите Happy в корзине. Регистр букв не важен: happy, HAPPY и Happy работают одинаково. Расчёт предварительный — менеджер подтвердит дату рождения до оплаты.","Ծննդյան օրը զամբյուղում մուտքագրեք Happy։ Տառերի մեծությունը կարևոր չէ՝ happy, HAPPY և Happy նույնն են։ Հաշվարկը նախնական է․ մենեջերը կհաստատի ծննդյան ամսաթիվը վճարումից առաջ։","Enter Happy in your bag on your birthday. Letter case does not matter: happy, HAPPY and Happy are equivalent. The discount is provisional until a manager verifies your birthday before payment.")+'</p><div class="promo-code"><code>Happy</code><button type="button" data-copy-promo="Happy">'+icon("overview")+t("Копировать","Պատճենել","Copy")+'</button></div><p>'+t("Потребуется подтверждение даты рождения. Покажите менеджеру документ с датой; загружать его на сайт не нужно.","Պահանջվում է ծննդյան ամսաթվի հաստատում։ Մենեջերին ցույց տվեք ամսաթվով փաստաթուղթը․ կայք վերբեռնելու կարիք չկա։","Birthday verification is required. Show the date on a document to the manager; do not upload it to the website.")+'</p></article></div><section class="offer-conditions"><h2>'+t("Как сочетаются скидки","Ինչպես են համադրվում զեղչերը","Combining discounts")+'</h2><p>'+t("Можно выбрать 10% на первый заказ, один промокод или скидку личного кабинета вместе с одним промокодом. Скидка на первый заказ с Happy не суммируется. Для Happy минимальной суммы нет; применение требует подтверждения дня рождения.","Կարելի է ընտրել առաջին պատվերի 10%-ը, մեկ պրոմոկոդ կամ անձնական զեղչը՝ մեկ պրոմոկոդի հետ։ Առաջին պատվերի զեղչը Happy-ի հետ չի գումարվում։ Happy-ն նվազագույն գումար չունի, սակայն պահանջում է ծննդյան օրվա հաստատում։","Choose 10% off your first order, one promo code, or your account discount with one promo code. The first-order offer cannot be combined with Happy. Happy has no minimum spend and requires birthday verification.")+'</p><p id="copy-promo-status" role="status"></p><a href="/catalog">'+t("Выбрать свет","Ընտրել լուսավորությունը","Find your light")+'</a></section>'

def render_privacy(write):
    body='<div class="info-cards"><section><h2>'+t("Фотография для примерки","Փորձարկման լուսանկարը","Your preview photo")+'</h2><p>'+t("Фото и пожелания отправляются с сайта в OpenAI только после нажатия кнопки запуска примерки. Загрузка файла для предпросмотра сама по себе не отправляет его на сервер. Использование остальных страниц сайта не означает согласия на передачу фото.","Լուսանկարն ու ցանկությունները կայքից OpenAI են ուղարկվում միայն փորձարկումը սկսելու կոճակը սեղմելուց հետո։ Ֆայլի նախադիտումը այն սերվեր չի ուղարկում։ Այլ էջերից օգտվելը չի նշանակում լուսանկարի փոխանցման համաձայնություն։","Your photo and wishes are sent from the website to OpenAI only when you start a preview. Selecting a file for local preview does not upload it. Browsing other pages does not imply consent to photo processing.")+'</p><p>'+t("Используйте фото без людей, документов и личных данных. Загружайте только изображения, которыми вправе распоряжаться. ИИ создаёт приблизительную визуализацию: она не заменяет проверку размеров, креплений, электрики и расчёт освещённости.","Օգտագործեք լուսանկարներ առանց մարդկանց, փաստաթղթերի և անձնական տվյալների։ Վերբեռնեք միայն ձեր օգտագործման իրավունքով պատկերներ։ ԱԲ-ի մոտավոր պատկերը չի փոխարինում չափերի, ամրակների, էլեկտրականության և լուսավորվածության ստուգմանը։","Use photos without people, documents or personal information, and only images you have the right to use. AI previews are approximate and do not replace checks of dimensions, mounting, electrical installation or illumination.")+'</p><p>'+t("Перед передачей учитывайте правила обработки данных OpenAI. Запрос по данным LUSAR можно направить через контакты магазина. Условия хранения и обработки у поставщика проверяйте по его действующей политике.","Փոխանցելուց առաջ ծանոթացեք OpenAI-ի տվյալների մշակման կանոններին։ LUSAR-ի տվյալների հարցերով դիմեք խանութի կոնտակտներով։ Մատակարարի պահպանման և մշակման պայմանները ստուգեք գործող քաղաքականությամբ։","Review OpenAI data handling terms before submitting. Contact the store for requests concerning LUSAR-held data. Check the provider's current policy for its retention and processing terms.")+'</p><a href="https://openai.com/policies/privacy-policy/">OpenAI · Privacy Policy</a><p><a href="/contacts">'+t("Контакты","Կոնտակտներ","Contacts")+'</a></p></section></div>'
    write("legal/ai","Условия использования Lusar AI и аккаунта",body,draft=True)
    write("legal/privacy","Конфиденциальность",'<p class="lead">'+t("Информация об обработке фотографий в Lusar AI. Полная политика сайта дополняется реквизитами оператора перед запуском.","Տեղեկություն Lusar AI-ի լուսանկարների մշակման մասին։ Կայքի ամբողջական քաղաքականությունը մինչև գործարկումը կլրացվի օպերատորի տվյալներով։","Information about Lusar AI photo processing. The full site policy requires operator details before launch.")+'</p>'+body,draft=True)
