"""Public commercial and legal information approved for the existing storefront."""
import business as b
from storefront_design import t


def render(write, card, actions):
    for entry in [
        ('Подбор освещения', 'Լուսավորության ընտրություն', 'Choosing lighting'),
        ('Сотрудничество', 'Համագործակցություն', 'Partnerships'),
        ('Магазин', 'Խանութ', 'Store'),
        ('Уведомления', 'Ծանուցումներ', 'Notifications'),
        ('Наличие, способ получения и итоговую сумму уточнит менеджер.', 'Առկայությունը, ստացման եղանակն ու վերջնական գումարը կճշտի մենեջերը։', 'A manager will confirm availability, collection arrangements and the final total.'),
        ('Принимаем наличные, банковские карты и банковские переводы. Детали оплаты согласовываются индивидуально с менеджером.',
         'Ընդունում ենք կանխիկ, բանկային քարտեր և բանկային փոխանցումներ։ Վճարման մանրամասները անհատապես համաձայնեցվում են մենեջերի հետ։',
         'We accept cash, bank cards and bank transfers. Payment details are agreed individually with a manager.'),
        ('Вы получите номер заявки и ссылку для проверки статуса. Менеджер свяжется с вами для подтверждения заказа.',
         'Կստանաք հայտի համարը և կարգավիճակը ստուգելու հղումը։ Մենեջերը կապ կհաստատի ձեզ հետ՝ պատվերը հաստատելու համար։',
         'You receive a request number and a status link. A manager will contact you to confirm your order.')
    ]:
        t(*entry)
    def p(ru, hy, en):
        return '<p>' + t(ru, hy, en) + '</p>'

    def page(path, title, sections, description):
        write(path, t(*title), ('<div class="info-cards info-cards-pair">' if len(sections) == 2 else '<div class="info-cards">') + ''.join(
            card(icon, t(*heading), body, featured=i == 0)
            for i, (icon, heading, body) in enumerate(sections)) + '</div>' +
            actions((("contacts", "Контакты"), ("catalog", "Каталог"))), description=t(*description))

    contact = b.contact(t)
    address = '<address>' + t(*b.CONFIG['address']) + '</address>'
    store = card('pin', t('Магазин LUSAR', 'LUSAR խանութը', 'LUSAR store'), address + b.maps(t))
    details = contact + b.socials(t)
    write('contacts', t('Контакты LUSAR', 'LUSAR-ի կոնտակտները', 'Contact LUSAR'),
          '<div class="info-cards info-cards-pair">' + card('phone', t('На связи', 'Կապ մեզ հետ', 'Get in touch'), details, featured=True) + store + '</div>',
          description=t('Контакты LUSAR: +374 (98) 30-09-90, Ереван Маркет, С. Зоравар 11/1, D50. Ежедневно 09:30–19:00.',
                        'LUSAR․ +374 (98) 30-09-90, Ս. Զորավար 11/1, Երևան Տոնավաճառ, D50։ Ամեն օր՝ 09:30–19:00։',
                        'Contact LUSAR: +374 (98) 30-09-90, Yerevan Market, 11/1 S. Zoravar, D50. Daily 09:30–19:00.'))
    write('stores', t('Магазин LUSAR', 'LUSAR խանութը', 'LUSAR store'), '<div class="info-cards">' + store + '</div>',
          description=t('Магазин LUSAR в Ереване: Ереван Маркет, С. Зоравар 11/1, павильон D50.',
                        'LUSAR խանութը՝ Ս. Զորավար 11/1, Երևան Տոնավաճառ, D50 տաղավար։',
                        'The LUSAR store in Yerevan: Yerevan Market, 11/1 S. Zoravar Street, pavilion D50.'))
    write(b.CONFIG['storePath'], t('LUSAR · Ереван Маркет, D50', 'LUSAR · Երևան Տոնավաճառ, D50', 'LUSAR · Yerevan Market, D50'),
          '<div class="info-cards info-cards-pair">' + store + card('phone', t('На связи'), details) + '</div>',
          description=t(*b.CONFIG['address']), structured_data={
              '@context': 'https://schema.org', '@type': 'Store', '@id': 'https://lusar.am/#store',
              'name': 'LUSAR', 'legalName': b.CONFIG['seller'], 'taxID': b.CONFIG['taxId'],
              'url': 'https://lusar.am/' + b.CONFIG['storePath'], 'telephone': b.CONFIG['phone'], 'email': b.CONFIG['email'],
              'address': {'@type': 'PostalAddress', 'streetAddress': '11/1 S. Zoravar Street, Yerevan Market, D50', 'addressLocality': 'Yerevan', 'addressCountry': 'AM'},
              'openingHoursSpecification': {'@type': 'OpeningHoursSpecification', 'dayOfWeek': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], 'opens': '09:30', 'closes': '19:00'}})

    page('about', ('О LUSAR', 'LUSAR-ի մասին', 'About LUSAR'), [
        ('spark', ('Свет для вашего пространства', 'Լույս՝ ձեր տարածքի համար', 'Lighting for your space'), p(
            'Люстры, хрустальные светильники, LED-системы, магнитные треки, бра и торшеры — для дома и других пространств.',
            'Ջահեր, բյուրեղյա լուսատուներ, LED համակարգեր, մագնիսական ռելսեր, պատի և հատակի լուսատուներ՝ տան և այլ տարածքների համար։',
            'Chandeliers, crystal fixtures, LED systems, magnetic tracks, wall lights and floor lamps for your home and other spaces.')),
        ('lamp', ('Ассортимент и качество', 'Տեսականի և որակ', 'Range and quality'), p(
            'Регулярно обновляем коллекции и тщательно выбираем продукцию. В ассортименте — освещение для разных стилей и бюджетов.',
            'Պարբերաբար թարմացնում ենք հավաքածուները և խնամքով ընտրում ապրանքները։ Տեսականին ներառում է լուսավորություն տարբեր ոճերի և բյուջեների համար։',
            'We regularly refresh our collections and carefully select our products, with lighting for different styles and budgets.')),
        ('orders', ('Розница и сотрудничество', 'Մանրածախ և համագործակցություն', 'Retail and partnerships'), p(
            'Работаем с частными покупателями, магазинами и оптовыми партнёрами. Условия крупных закупок обсуждаем индивидуально.',
            'Աշխատում ենք անհատ գնորդների, խանութների և մեծածախ գործընկերների հետ։ Խոշոր գնումների պայմանները քննարկում ենք անհատապես։',
            'We work with individual customers, stores and wholesale partners. Large purchases are discussed individually.') + actions((("professionals", "Дизайнерам и бизнесу"),))),
        ('pin', ('Наш магазин', 'Մեր խանութը', 'Our store'), address + b.maps(t))
    ], ('LUSAR — освещение для разных интерьеров, широкий ассортимент, розничные и оптовые продажи в Ереване.',
        'LUSAR՝ լուսավորություն տարբեր ինտերիերների համար, լայն տեսականի, մանրածախ և մեծածախ վաճառք Երևանում։',
        'LUSAR lighting for different interiors: a broad range, retail and wholesale in Yerevan.'))

    page('delivery', ('Доставка и самовывоз', 'Առաքում և ինքնառաքում', 'Delivery and collection'), [
        ('pin', ('Самовывоз из магазина', 'Ստացում խանութից', 'Collect from the store'), p(
            'Заберите заказ в магазине. Перед поездкой уточните наличие у менеджера.',
            'Վերցրեք պատվերը խանութից։ Այցից առաջ առկայությունը ճշտեք մենեջերից։',
            'Collect your order from the store. Confirm availability with a manager before visiting.') + address),
        ('delivery', ('Доставка по согласованию', 'Առաքում՝ համաձայնությամբ', 'Delivery by arrangement'), p(
            'Возможность, стоимость и сроки доставки уточняйте по телефону.',
            'Առաքման հնարավորությունը, արժեքն ու ժամկետները ճշտեք հեռախոսով։',
            'Call us to discuss delivery availability, cost and timing.') + b.phone())
    ], ('Самовывоз из LUSAR в Ереван Маркет, D50. Возможность, стоимость и сроки доставки обсуждаются по телефону.',
        'Ստացում LUSAR-ից՝ Երևան Տոնավաճառ, D50։ Առաքման հնարավորությունը, արժեքն ու ժամկետները քննարկվում են հեռախոսով։',
        'Collect from LUSAR at Yerevan Market, D50. Delivery availability, cost and timing are discussed by phone.'))

    payment = p('Наличные, банковская карта или перевод. Условия предоплаты уточняйте у менеджера.',
                'Կանխիկ, բանկային քարտ կամ փոխանցում։ Կանխավճարի պայմանները ճշտեք մենեջերից։',
                'Cash, bank card or bank transfer. Ask a manager about prepayment terms.')
    request = p('Отправьте заявку, указав имя и телефон. Менеджер подтвердит наличие и итоговую стоимость. Оплата — после согласования заказа.',
                'Ուղարկեք հայտը՝ նշելով անունն ու հեռախոսը։ Մենեջերը կհաստատի առկայությունն ու վերջնական արժեքը։ Վճարումը՝ պատվերը համաձայնեցնելուց հետո։',
                'Send a request with your name and phone number. A manager will confirm availability and the final price. Payment follows order confirmation.')
    page('payment', ('Оплата', 'Վճարում', 'Payment'), [
        ('orders', ('Заявка без онлайн-оплаты', 'Հայտ՝ առանց առցանց վճարման', 'Request without online payment'), request),
        ('check', ('Способы оплаты', 'Վճարման եղանակներ', 'Payment methods'), payment)
    ], ('Оплата LUSAR: наличные, банковская карта или перевод. Стоимость и условия подтверждает менеджер, онлайн-оплаты нет.',
        'LUSAR-ի վճարում՝ կանխիկ, քարտ կամ փոխանցում։ Արժեքն ու պայմանները հաստատում է մենեջերը․ առցանց վճարում չկա։',
        'Pay LUSAR by cash, bank card or transfer. A manager confirms the price and terms; there is no online payment.'))

    rights = p('Условия магазина не ограничивают ваши права по законодательству Республики Армения.',
               'Խանութի պայմանները չեն սահմանափակում ձեր իրավունքները՝ Հայաստանի Հանրապետության օրենսդրությամբ։',
               'Store terms do not limit your rights under Armenian law.')
    page('returns', ('Гарантия, обмен и возврат', 'Երաշխիք, փոխանակում և վերադարձ', 'Warranty, exchange and returns'), [
        ('check', ('Гарантия на конкретный товар', 'Կոնկրետ ապրանքի երաշխիք', 'Product-specific warranty'), p(
            'Срок и условия гарантии уточняйте у менеджера для выбранной модели до покупки.',
            'Ընտրված մոդելի երաշխիքի ժամկետն ու պայմանները ճշտեք մենեջերից մինչև գնումը։',
            'Ask a manager about the selected model’s warranty period and terms before buying.')),
        ('orders', ('Товар надлежащего качества', 'Պատշաճ որակի ապրանք', 'Goods of satisfactory quality'), p(
            'Обмен и возврат — по законодательству Республики Армения. Для качественного товара учитываются установленные законом сроки, исключения, состояние и комплектация.',
            'Փոխանակումն ու վերադարձը՝ ՀՀ օրենսդրությամբ։ Որակյալ ապրանքի համար հաշվի են առնվում օրենքով սահմանված ժամկետները, բացառությունները, վիճակն ու լրակազմը։',
            'Exchanges and returns follow Armenian law. For satisfactory goods, statutory periods, exceptions, condition and completeness requirements apply.')),
        ('phone', ('Если обнаружен недостаток', 'Թերության հայտնաբերման դեպքում', 'If you discover a defect'), p(
            'Свяжитесь с менеджером и опишите недостаток. Обращения по дефектам рассматриваются отдельно от возврата качественного товара — с сохранением ваших законных прав.',
            'Կապվեք մենեջերի հետ և նկարագրեք թերությունը։ Թերությունների դիմումները դիտարկվում են որակյալ ապրանքի վերադարձից առանձին՝ պահպանելով ձեր օրինական իրավունքները։',
            'Contact a manager and describe the defect. Defect claims are handled separately from returns of satisfactory goods, with your statutory rights preserved.') + b.phone()),
        ('overview', ('Права покупателя', 'Գնորդի իրավունքները', 'Consumer rights'), rights)
    ], ('Гарантия зависит от товара. Обмен, возврат и обращения по дефектам в LUSAR — по законодательству Республики Армения.',
        'Երաշխիքը կախված է ապրանքից։ LUSAR-ի փոխանակումը, վերադարձն ու թերությունների դիմումները՝ ՀՀ օրենսդրությամբ։',
        'Warranty depends on the product. LUSAR exchanges, returns and defect claims follow Armenian law.'))

    cooperation = p('Сотрудничаем с магазинами, оптовыми партнёрами, дизайнерами, архитекторами и строительными компаниями. Цены и условия закупок обсуждаем индивидуально.',
                    'Համագործակցում ենք խանութների, մեծածախ գործընկերների, դիզայներների, ճարտարապետների և շինարարական ընկերությունների հետ։ Գներն ու գնման պայմանները քննարկում ենք անհատապես։',
                    'We work with stores, wholesale partners, designers, architects and construction companies. Prices and purchasing terms are discussed individually.')
    for route in ('professionals', 'partners'):
        page(route, ('Сотрудничество с LUSAR', 'Համագործակցություն LUSAR-ի հետ', 'Partner with LUSAR'), [
            ('desk', ('Для профессионалов и бизнеса', 'Մասնագետների և բիզնեսի համար', 'For professionals and businesses'), cooperation),
            ('phone', ('Обсудим вашу закупку', 'Քննարկենք ձեր գնումը', 'Discuss your purchase'), p(
                'Сообщите менеджеру модели и количество — уточним наличие и условия.',
                'Մենեջերին հայտնեք մոդելներն ու քանակը՝ կճշտենք առկայությունն ու պայմանները։',
                'Tell the manager which models and quantities you need — we’ll confirm availability and terms.') + contact)
        ], ('Розничные и оптовые закупки, сотрудничество с дизайнерами, архитекторами и магазинами. Индивидуальные условия LUSAR.',
            'Մանրածախ և մեծածախ գնումներ, համագործակցություն դիզայներների, ճարտարապետների և խանութների հետ։ LUSAR-ի անհատական պայմաններ։',
            'Retail and wholesale purchases, partnerships with designers, architects and stores. Individual terms from LUSAR.'))

    page('legal/terms', ('Условия заявок и продажи', 'Հայտերի և վաճառքի պայմաններ', 'Request and sale terms'), [
        ('orders', ('Сведения о продавце', 'Վաճառողի տվյալները', 'Seller details'), b.seller(t) + contact),
        ('check', ('Порядок оформления', 'Ձևակերպման կարգը', 'Placing a request'), request),
        ('overview', ('Стоимость и получение', 'Արժեքը և ստացումը', 'Price and collection'), payment + p(
            'Итог в корзине предварительный. До оплаты менеджер подтверждает наличие, сумму с применимыми скидками и способ получения. Основной способ — самовывоз; возможность доставки обсуждается по телефону. Отправка заявки не является онлайн-оплатой.',
            'Զամբյուղի գումարը նախնական է։ Մինչև վճարումը մենեջերը հաստատում է առկայությունը, կիրառելի զեղչերով գումարն ու ստացման եղանակը։ Հիմնական եղանակը խանութից ստանալն է․ առաքման հնարավորությունը քննարկվում է հեռախոսով։ Հայտի ուղարկումը առցանց վճարում չէ։',
            'The bag total is provisional. Before payment, a manager confirms availability, the amount including applicable discounts and collection arrangements. Store collection is the main option; delivery is discussed by phone. Sending a request is not an online payment.')),
        ('phone', ('Обращения и права', 'Դիմումներ և իրավունքներ', 'Enquiries and rights'), rights + actions((("returns", "Гарантия и возврат"), ("legal/privacy", "Конфиденциальность"), ("legal/loyalty", "Условия акций и скидок"))))
    ], ('Luys+ LLC, налоговый номер 02333832: порядок заявок LUSAR, согласование стоимости, оплаты и получения.',
        'Luys+ LLC, ՀՎՀՀ 02333832․ LUSAR-ի հայտերի կարգը, արժեքի, վճարման և ստացման համաձայնեցումը։',
        'Luys+ LLC, tax ID 02333832: LUSAR requests, price confirmation, payment and collection arrangements.'))

    page('legal/privacy', ('Политика конфиденциальности', 'Գաղտնիության քաղաքականություն', 'Privacy policy'), [
        ('orders', ('Оператор и связь', 'Մշակողը և կապը', 'Controller and contact'), b.seller(t) + p(
            'По вопросам обработки ваших данных на сайте LUSAR обращайтесь по указанному email или в магазин.',
            'LUSAR կայքում ձեր տվյալների մշակման հարցերով դիմեք նշված էլ. փոստով կամ խանութ։',
            'For questions about your data on the LUSAR website, contact the email below or the store.') + contact),
        ('account', ('Данные и цели', 'Տվյալներ և նպատակներ', 'Data and purposes'), p(
            'Для обработки заявки используются имя, телефон, выбранные товары и сведения о заказе; email и адрес добавляются по желанию. Аккаунт использует данные входа и профиля, историю заказов, сохранённые адреса и списки товаров. Эти сведения нужны для связи, выполнения заявки, работы аккаунта и скидок.',
            'Հայտը մշակելու համար օգտագործվում են անունը, հեռախոսը, ընտրված ապրանքներն ու պատվերի տվյալները․ էլ. փոստն ու հասցեն ավելացվում են ըստ ցանկության։ Հաշիվն օգտագործում է մուտքի և պրոֆիլի տվյալները, պատվերների պատմությունը, պահպանված հասցեներն ու ապրանքացանկերը։ Դրանք անհրաժեշտ են կապի, հայտի կատարման, հաշվի և զեղչերի աշխատանքի համար։',
            'Requests use your name, phone, selected products and order details; email and address are optional. Accounts use sign-in and profile data, order history, saved addresses and product lists. These support communication, request handling, accounts and discounts.')),
        ('overview', ('Сервисы сайта', 'Կայքի ծառայությունները', 'Website services'), p(
            'Сайт размещён на Render. Вход в аккаунт выполняется через Auth0, а при выборе Google — также через Google. Уполномоченные сотрудники работают с заявками; уведомления о них направляются в служебный Telegram. Статистика Google Analytics и Яндекс Метрики включается при разрешении статистики и наличии настройки сервиса. Для защиты сайта обрабатываются технические сведения о запросах и попытках использования.',
            'Կայքը տեղակայված է Render-ում։ Հաշվի մուտքն իրականացվում է Auth0-ով, իսկ Google ընտրելու դեպքում՝ նաև Google-ով։ Լիազորված աշխատակիցները մշակում են հայտերը․ ծանուցումներն ուղարկվում են ծառայողական Telegram։ Google Analytics-ի և Յանդեքս Մետրիկայի վիճակագրությունը միանում է թույլտվության և ծառայության կարգավորման դեպքում։ Կայքի պաշտպանության համար մշակվում են հարցումների և օգտագործման փորձերի տեխնիկական տվյալները։',
            'The site is hosted on Render. Account sign-in uses Auth0 and, if selected, Google. Authorised staff handle requests; notifications go to the staff Telegram channel. Google Analytics and Yandex Metrica operate when configured and statistics are permitted. Technical request and usage-attempt information is processed to protect the site.')),
        ('spark', ('Фотографии и AI', 'Լուսանկարներ և ԱԲ', 'Photos and AI'), p(
            'При запуске AI-примерки фото и пожелания передаются OpenAI для обработки. В Telegram-боте данные проходят также через Telegram. Не отправляйте фото людей, документов или другие личные сведения. Перед использованием ознакомьтесь с условиями AI и политиками соответствующих сервисов.',
            'ԱԲ փորձարկումը սկսելու ժամանակ լուսանկարն ու ցանկությունները մշակման համար փոխանցվում են OpenAI-ին։ Telegram բոտում տվյալներն անցնում են նաև Telegram-ով։ Մի ուղարկեք մարդկանց, փաստաթղթերի լուսանկարներ կամ այլ անձնական տեղեկություններ։ Օգտագործելուց առաջ ծանոթացեք ԱԲ-ի պայմաններին և համապատասխան ծառայությունների քաղաքականություններին։',
            'Starting an AI preview sends your photo and wishes to OpenAI for processing. In the Telegram bot, data also pass through Telegram. Do not send photos of people, documents or other personal information. Review the AI terms and relevant service policies before use.') + actions((("legal/ai", "Условия использования Lusar AI и аккаунта"),))),
        ('phone', ('Ваши права', 'Ձեր իրավունքները', 'Your rights'), p(
            'Вы можете запросить сведения об обработке ваших данных, их исправление, блокирование или удаление в предусмотренных законом случаях, а также отозвать согласие на обработку, основанную на согласии. Напишите на email магазина, указав суть обращения; не отправляйте лишние документы. Отзыв согласия не отменяет обработку, необходимую по закону. Вы вправе обратиться в уполномоченный орган по защите персональных данных или в суд.',
            'Կարող եք պահանջել տեղեկություններ ձեր տվյալների մշակման մասին, դրանց ուղղում, արգելափակում կամ ջնջում՝ օրենքով նախատեսված դեպքերում, ինչպես նաև հետ կանչել համաձայնության վրա հիմնված մշակման համաձայնությունը։ Գրեք խանութի էլ. փոստին՝ նշելով դիմումի էությունը․ ավելորդ փաստաթղթեր մի ուղարկեք։ Համաձայնության հետկանչը չի վերացնում օրենքով անհրաժեշտ մշակումը։ Իրավունք ունեք դիմելու անձնական տվյալների պաշտպանության լիազոր մարմին կամ դատարան։',
            'You may request information about processing, correction, blocking or deletion where provided by law, and withdraw consent for consent-based processing. Email the store with your request; do not send unnecessary documents. Withdrawal does not override processing required by law. You may contact the authorised personal data protection body or a court.')),
        ('filter', ('Хранение и настройки', 'Պահպանում և կարգավորումներ', 'Storage and preferences'), p(
            'Обработка ограничивается необходимыми для заявленных целей данными и применимыми законными основаниями. Вопросы о сроке хранения ваших конкретных данных и об их передаче поставщикам сервисов можно направить оператору. Локальные настройки удаляются средствами браузера; статистику можно отключить через «Настройки cookie». Удаление данных браузера не удаляет сохранённые заявки или аккаунт.',
            'Մշակումը սահմանափակվում է նշված նպատակների համար անհրաժեշտ տվյալներով և կիրառելի օրինական հիմքերով։ Ձեր կոնկրետ տվյալների պահպանման ժամկետի և ծառայություններ մատուցողներին փոխանցման հարցերը կարող եք ուղղել մշակողին։ Տեղական կարգավորումները ջնջվում են դիտարկիչով․ վիճակագրությունը կարելի է անջատել cookie-ի կարգավորումներում։ Դիտարկիչի տվյալների ջնջումը չի ջնջում պահպանված հայտերը կամ հաշիվը։',
            'Processing is limited to data needed for the stated purposes and applicable lawful grounds. Ask the controller about retention of your specific data and disclosures to service providers. Browser tools clear local preferences; Cookie settings disable statistics. Clearing browser data does not delete saved requests or your account.') + actions((("legal/cookies", "Политика cookie"),)))
    ], ('Обработка данных LUSAR: Luys+ LLC, заявки, аккаунт, AI, cookie, сервисы и обращения по персональным данным.',
        'LUSAR-ի տվյալների մշակում՝ Luys+ LLC, հայտեր, հաշիվ, ԱԲ, cookie, ծառայություններ և անձնական տվյալների դիմումներ։',
        'LUSAR data processing: Luys+ LLC, requests, accounts, AI, cookies, services and personal data enquiries.'))

    page('news', ('Новости LUSAR', 'LUSAR-ի նորությունները', 'LUSAR news'), [
        ('lamp', ('Коллекции и ассортимент', 'Հավաքածուներ և տեսականի', 'Collections and range'), p(
            'Откройте каталог и познакомьтесь с коллекциями освещения LUSAR.',
            'Բացեք կատալոգը և ծանոթացեք LUSAR-ի լուսավորության հավաքածուներին։',
            'Explore the catalogue and discover LUSAR lighting collections.'))
    ], ('Обновления ассортимента и коллекций освещения LUSAR.', 'LUSAR-ի տեսականու և լուսավորության հավաքածուների նորությունները։', 'Updates to LUSAR lighting collections and range.'))
