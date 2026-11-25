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
        ('Вы получите номер и приватную ссылку для проверки статуса. Менеджер подтвердит наличие, итоговую сумму и способ получения. Обычно связываемся в течение 15 минут в рабочее время; сложные заказы могут занять больше времени. Вне рабочего времени заявки обрабатываем после открытия.',
         'Կստանաք հայտի համարը և կարգավիճակը ստուգելու անձնական հղումը։ Մենեջերը կհաստատի առկայությունը, վերջնական գումարն ու ստացման եղանակը։ Աշխատանքային ժամերին սովորաբար կապվում ենք 15 րոպեի ընթացքում․ բարդ պատվերները կարող են ավելի երկար տևել։ Ոչ աշխատանքային ժամերի հայտերը մշակում ենք բացվելուց հետո։',
         'You receive a reference number and a private status link. A manager confirms availability, the final total and collection arrangements. We usually contact you within 15 minutes during opening hours; complex orders may take longer. Requests outside opening hours are handled after reopening.')
    ]:
        t(*entry)
    def p(ru, hy, en):
        return '<p>' + t(ru, hy, en) + '</p>'

    def page(path, title, sections, description):
        write(path, t(*title), '<div class="info-cards">' + ''.join(
            card(icon, t(*heading), body, featured=i == 0)
            for i, (icon, heading, body) in enumerate(sections)) + '</div>' +
            actions((("contacts", "Контакты"), ("catalog", "Каталог"))), description=t(*description))

    contact = b.contact(t)
    address = '<address>' + t(*b.CONFIG['address']) + '</address>'
    store = card('pin', t('Единственный магазин LUSAR', 'LUSAR-ի միակ խանութը', 'The LUSAR store'), address + b.maps(t))
    details = contact + b.response_note(t) + b.socials(t)
    write('contacts', t('Контакты LUSAR', 'LUSAR-ի կոնտակտները', 'Contact LUSAR'),
          '<div class="info-cards">' + card('phone', t('На связи', 'Կապ մեզ հետ', 'Get in touch'), details, featured=True) + store +
          card('orders', t('Сведения о продавце', 'Վաճառողի տվյալները', 'Seller details'), b.seller(t)) + '</div>',
          description=t('Контакты LUSAR: +374 (98) 30-09-90, Ереван Маркет, С. Зоравар 11/1, D50. Ежедневно 09:30–19:00.',
                        'LUSAR․ +374 (98) 30-09-90, Ս. Զորավար 11/1, Երևան Տոնավաճառ, D50։ Ամեն օր՝ 09:30–19:00։',
                        'Contact LUSAR: +374 (98) 30-09-90, Yerevan Market, 11/1 S. Zoravar, D50. Daily 09:30–19:00.'))
    write('stores', t('Магазин LUSAR', 'LUSAR խանութը', 'LUSAR store'), '<div class="info-cards">' + store + '</div>',
          description=t('Один магазин LUSAR в Ереване: Ереван Маркет, С. Зоравар 11/1, павильон D50.',
                        'LUSAR-ի միակ խանութը՝ Ս. Զորավար 11/1, Երևան Տոնավաճառ, D50 տաղավար։',
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
            'LUSAR — магазин освещения для разных интерьеров и задач. Декоративные люстры, хрустальные светильники, LED-системы, магнитные треки, бра, торшеры и комплектующие помогают создать свой световой сценарий.',
            'LUSAR-ը լուսավորության խանութ է տարբեր ինտերիերների և խնդիրների համար։ Դեկորատիվ ջահերը, բյուրեղյա լուսատուները, LED համակարգերը, մագնիսական ռելսերը, պատի և հատակի լուսատուներն ու բաղադրիչները կօգնեն ստեղծել ձեր լուսավորությունը։',
            'LUSAR offers lighting for different interiors and needs: decorative chandeliers, crystal fixtures, LED systems, magnetic tracks, wall lights, floor lamps and components for your own lighting scheme.')),
        ('lamp', ('Ассортимент и качество', 'Տեսականի և որակ', 'Range and quality'), p(
            'Мы регулярно обновляем коллекции и внимательно выбираем продукцию и производителей. При необходимости отдельные комплектующие заменяются на более качественные для повышения надёжности. В ассортименте есть решения разных ценовых категорий.',
            'Մենք պարբերաբար թարմացնում ենք հավաքածուները և ուշադիր ընտրում ապրանքներն ու արտադրողներին։ Անհրաժեշտության դեպքում առանձին բաղադրիչները փոխարինվում են ավելի որակյալներով՝ հուսալիությունը բարձրացնելու համար։ Տեսականին ներառում է տարբեր գնային կարգերի լուծումներ։',
            'We regularly refresh our collections and carefully select products and manufacturers. Where needed, individual components are replaced with higher-quality alternatives to improve reliability. The range includes different price points.')),
        ('orders', ('Розница и сотрудничество', 'Մանրածախ և համագործակցություն', 'Retail and partnerships'), p(
            'Работаем с частными покупателями, магазинами и оптовыми партнёрами. Сотрудники консультируют по ассортименту и характеристикам товаров. Условия крупных закупок обсуждаем индивидуально.',
            'Աշխատում ենք անհատ գնորդների, խանութների և մեծածախ գործընկերների հետ։ Աշխատակիցները խորհրդատվություն են տրամադրում տեսականու և ապրանքների բնութագրերի վերաբերյալ։ Խոշոր գնումների պայմանները քննարկում ենք անհատապես։',
            'We work with individual customers, stores and wholesale partners. Our staff advise on the range and product specifications. Large purchases are discussed individually.') + actions((("professionals", "Дизайнерам и бизнесу"),))),
        ('pin', ('Магазин и продавец', 'Խանութ և վաճառող', 'Store and seller'), address + b.seller(t))
    ], ('LUSAR — освещение для разных интерьеров, широкий ассортимент, розничные и оптовые продажи в Ереване.',
        'LUSAR՝ լուսավորություն տարբեր ինտերիերների համար, լայն տեսականի, մանրածախ և մեծածախ վաճառք Երևանում։',
        'LUSAR lighting for different interiors: a broad range, retail and wholesale in Yerevan.'))

    page('delivery', ('Доставка и самовывоз', 'Առաքում և ինքնառաքում', 'Delivery and collection'), [
        ('pin', ('Самовывоз из магазина', 'Ստացում խանութից', 'Collect from the store'), p(
            'Основной способ получения — самовывоз. Если товар есть в наличии, его можно забрать в магазине. Перед поездкой уточните наличие, а для крупного заказа заранее свяжитесь с менеджером.',
            'Ստացման հիմնական եղանակը խանութից վերցնելն է։ Առկա ապրանքը կարող եք վերցնել խանութից։ Այցից առաջ ճշտեք առկայությունը, իսկ խոշոր պատվերի դեպքում նախապես կապվեք մենեջերի հետ։',
            'Collection is the main way to receive your order. In-stock items can be collected from the store. Confirm availability before travelling and contact a manager in advance for a large order.') + address),
        ('delivery', ('Доставка по согласованию', 'Առաքում՝ համաձայնությամբ', 'Delivery by arrangement'), p(
            'Собственной службы доставки у LUSAR нет. Возможность организации доставки, стоимость, условия и сроки обсуждаются индивидуально по телефону до согласования заказа.',
            'LUSAR-ը սեփական առաքման ծառայություն չունի։ Առաքման կազմակերպման հնարավորությունը, արժեքը, պայմաններն ու ժամկետները քննարկվում են անհատապես հեռախոսով՝ պատվերը համաձայնեցնելուց առաջ։',
            'LUSAR does not operate its own delivery service. Delivery availability, cost, terms and timing are discussed individually by phone before the order is agreed.') + b.phone()),
        ('orders', ('После заявки', 'Հայտից հետո', 'After your request'), b.response_note(t))
    ], ('Самовывоз из LUSAR в Ереван Маркет, D50. Возможность, стоимость и сроки доставки обсуждаются по телефону.',
        'Ստացում LUSAR-ից՝ Երևան Տոնավաճառ, D50։ Առաքման հնարավորությունը, արժեքն ու ժամկետները քննարկվում են հեռախոսով։',
        'Collect from LUSAR at Yerevan Market, D50. Delivery availability, cost and timing are discussed by phone.'))

    payment = p('Принимаем наличные, банковские карты и банковские переводы. Предоплата, расчёты по крупным заказам и остальные детали согласовываются с менеджером индивидуально.',
                'Ընդունում ենք կանխիկ, բանկային քարտեր և բանկային փոխանցումներ։ Կանխավճարը, խոշոր պատվերների հաշվարկներն ու մյուս մանրամասները անհատապես համաձայնեցվում են մենեջերի հետ։',
                'We accept cash, bank cards and bank transfers. Prepayment, settlement for large orders and other details are agreed individually with a manager.')
    request = p('На сайте вы отправляете заявку без онлайн-оплаты. Обязательны только имя и телефон; email и адрес — по желанию. Менеджер проверяет фактическое наличие, окончательную стоимость и согласовывает дальнейшие действия.',
                'Կայքում ուղարկում եք հայտ՝ առանց առցանց վճարման։ Պարտադիր են միայն անունն ու հեռախոսը․ էլ. փոստն ու հասցեն՝ ըստ ցանկության։ Մենեջերը ստուգում է փաստացի առկայությունը, վերջնական արժեքը և համաձայնեցնում հետագա քայլերը։',
                'The website accepts requests without online payment. Only your name and phone are required; email and address are optional. A manager checks actual availability, the final price and agrees the next steps.')
    page('payment', ('Оплата', 'Վճարում', 'Payment'), [
        ('orders', ('Заявка без онлайн-оплаты', 'Հայտ՝ առանց առցանց վճարման', 'Request without online payment'), request),
        ('check', ('Способы оплаты', 'Վճարման եղանակներ', 'Payment methods'), payment),
        ('phone', ('Подтверждение менеджером', 'Հաստատում մենեջերի կողմից', 'Manager confirmation'), b.response_note(t))
    ], ('Оплата LUSAR: наличные, банковская карта или перевод. Стоимость и условия подтверждает менеджер, онлайн-оплаты нет.',
        'LUSAR-ի վճարում՝ կանխիկ, քարտ կամ փոխանցում։ Արժեքն ու պայմանները հաստատում է մենեջերը․ առցանց վճարում չկա։',
        'Pay LUSAR by cash, bank card or transfer. A manager confirms the price and terms; there is no online payment.'))

    rights = p('Эта информация не ограничивает обязательные права покупателя по законодательству Республики Армения. Условия конкретного товара уточняются до покупки; индивидуальное согласование не отменяет требований закона.',
               'Այս տեղեկությունը չի սահմանափակում գնորդի պարտադիր իրավունքները՝ Հայաստանի Հանրապետության օրենսդրությամբ։ Կոնկրետ ապրանքի պայմանները ճշտվում են մինչև գնումը․ անհատական համաձայնությունը չի վերացնում օրենքի պահանջները։',
               'This information does not limit mandatory consumer rights under Armenian law. Product-specific terms are clarified before purchase; individual arrangements do not override statutory requirements.')
    page('returns', ('Гарантия, обмен и возврат', 'Երաշխիք, փոխանակում և վերադարձ', 'Warranty, exchange and returns'), [
        ('check', ('Гарантия на конкретный товар', 'Կոնկրետ ապրանքի երաշխիք', 'Product-specific warranty'), p(
            'Гарантийный срок зависит от товара. Уточните срок и условия для выбранной модели у менеджера до покупки. Единого гарантийного срока для всего ассортимента нет.',
            'Երաշխիքային ժամկետը կախված է ապրանքից։ Ընտրված մոդելի ժամկետն ու պայմանները ճշտեք մենեջերից մինչև գնումը։ Ամբողջ տեսականու համար միասնական երաշխիքային ժամկետ չկա։',
            'Warranty periods depend on the product. Ask the manager about the selected model’s period and terms before purchase. There is no single warranty period for the entire range.')),
        ('orders', ('Товар надлежащего качества', 'Պատշաճ որակի ապրանք', 'Goods of satisfactory quality'), p(
            'Обмен и возврат осуществляются по законодательству Республики Армения. Для товара надлежащего качества применяются предусмотренные законом условия, сроки и исключения, в том числе требования к состоянию товара, сохранности его свойств и комплектации.',
            'Փոխանակումն ու վերադարձը կատարվում են ՀՀ օրենսդրությամբ։ Պատշաճ որակի ապրանքի համար կիրառվում են օրենքով նախատեսված պայմանները, ժամկետներն ու բացառությունները, այդ թվում՝ ապրանքի վիճակի, հատկությունների պահպանման և լրակազմի պահանջները։',
            'Exchanges and returns follow Armenian law. Goods of satisfactory quality are subject to statutory conditions, periods and exceptions, including requirements concerning their condition, preserved properties and completeness.')),
        ('phone', ('Если обнаружен недостаток', 'Թերության հայտնաբերման դեպքում', 'If you discover a defect'), p(
            'Сообщите менеджеру о недостатке и укажите товар и сведения о покупке, которыми располагаете. Требования к товарному виду при возврате качественного товара не являются безусловным основанием отказать в обращении по дефекту. Ваши требования рассматриваются с учётом характера недостатка и применимого закона.',
            'Մենեջերին տեղեկացրեք թերության մասին՝ նշելով ապրանքը և գնման վերաբերյալ առկա տվյալները։ Որակյալ ապրանքի վերադարձի ժամանակ արտաքին տեսքի պահանջները թերության վերաբերյալ դիմումը մերժելու անվերապահ հիմք չեն։ Պահանջները դիտարկվում են՝ հաշվի առնելով թերության բնույթն ու կիրառելի օրենքը։',
            'Tell the manager about the defect and identify the product and any purchase details you have. Appearance requirements for returning satisfactory goods are not an unconditional reason to reject a defect claim. Claims are considered according to the defect and applicable law.') + b.phone()),
        ('overview', ('Права покупателя', 'Գնորդի իրավունքները', 'Consumer rights'), rights)
    ], ('Гарантия зависит от товара. Обмен, возврат и обращения по дефектам в LUSAR — по законодательству Республики Армения.',
        'Երաշխիքը կախված է ապրանքից։ LUSAR-ի փոխանակումը, վերադարձն ու թերությունների դիմումները՝ ՀՀ օրենսդրությամբ։',
        'Warranty depends on the product. LUSAR exchanges, returns and defect claims follow Armenian law.'))

    cooperation = p('Приглашаем к сотрудничеству магазины освещения, оптовых партнёров, дизайнеров интерьеров, архитекторов и строительные компании. Подбирайте товары из ассортимента LUSAR для своих задач и бюджета. Объёмы, цены и условия сотрудничества обсуждаются индивидуально.',
                    'Համագործակցության ենք հրավիրում լուսավորության խանութներին, մեծածախ գործընկերներին, ինտերիերի դիզայներներին, ճարտարապետներին և շինարարական ընկերություններին։ Ընտրեք LUSAR-ի տեսականուց՝ ձեր խնդիրներին ու բյուջեին համապատասխան։ Ծավալները, գներն ու պայմանները քննարկվում են անհատապես։',
                    'We welcome lighting stores, wholesale partners, interior designers, architects and construction companies. Choose from LUSAR’s range to suit your needs and budget. Quantities, prices and partnership terms are discussed individually.')
    for route in ('professionals', 'partners'):
        page(route, ('Сотрудничество с LUSAR', 'Համագործակցություն LUSAR-ի հետ', 'Partner with LUSAR'), [
            ('desk', ('Для профессионалов и бизнеса', 'Մասնագետների և բիզնեսի համար', 'For professionals and businesses'), cooperation),
            ('phone', ('Обсудим вашу закупку', 'Քննարկենք ձեր գնումը', 'Discuss your purchase'), p(
                'Сообщите менеджеру интересующие модели, количество и пожелания. Он проверит наличие и подготовит условия для вашего запроса.',
                'Մենեջերին հայտնեք հետաքրքրող մոդելները, քանակն ու ցանկությունները։ Նա կստուգի առկայությունը և կպատրաստի ձեր հարցման պայմանները։',
                'Tell the manager which models and quantities you need, together with any preferences. They will check availability and prepare terms for your enquiry.') + contact)
        ], ('Розничные и оптовые закупки, сотрудничество с дизайнерами, архитекторами и магазинами. Индивидуальные условия LUSAR.',
            'Մանրածախ և մեծածախ գնումներ, համագործակցություն դիզայներների, ճարտարապետների և խանութների հետ։ LUSAR-ի անհատական պայմաններ։',
            'Retail and wholesale purchases, partnerships with designers, architects and stores. Individual terms from LUSAR.'))

    page('legal/terms', ('Условия заявок и продажи', 'Հայտերի և վաճառքի պայմաններ', 'Request and sale terms'), [
        ('orders', ('Сведения о продавце', 'Վաճառողի տվյալները', 'Seller details'), b.seller(t) + contact),
        ('check', ('Порядок оформления', 'Ձևակերպման կարգը', 'Placing a request'), request + b.response_note(t)),
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
            'Коллекции LUSAR регулярно обновляются, а каталог сайта пополняется постепенно. Посмотрите опубликованные модели и уточните фактическое наличие у менеджера.',
            'LUSAR-ի հավաքածուները պարբերաբար թարմացվում են, իսկ կայքի կատալոգը համալրվում է աստիճանաբար։ Դիտեք հրապարակված մոդելները և փաստացի առկայությունը ճշտեք մենեջերից։',
            'LUSAR collections are regularly refreshed and the website catalogue is being expanded gradually. Explore published models and confirm actual availability with a manager.'))
    ], ('Обновления ассортимента и коллекций освещения LUSAR.', 'LUSAR-ի տեսականու և լուսավորության հավաքածուների նորությունները։', 'Updates to LUSAR lighting collections and range.'))
