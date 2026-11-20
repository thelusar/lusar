"""Useful launch pages based on implemented behavior, without invented terms."""
from storefront_design import t
from loyalty import LOYALTY_TIERS


def render(write, card, actions):
    def p(ru, hy, en):
        return '<p>' + t(ru, hy, en) + '</p>'

    write("selection", "Подбор освещения", '<div class="info-cards">' +
          card("sofa", t("Начните с пространства", "Սկսեք տարածքից", "Start with your space"),
               p("Выберите комнату и определите задачи: общий свет, чтение или акцент на деталях.",
                 "Ընտրեք սենյակը և լույսի նպատակը՝ ընդհանուր լուսավորում, ընթերցանություն կամ շեշտադրում։",
                 "Choose a room and a purpose: general lighting, reading or a detail to highlight.") + actions((("rooms", "По комнатам"),)), featured=True) +
          card("lamp", t("Сверьте размеры", "Ստուգեք չափերը", "Check the dimensions"),
               p("Измерьте высоту потолка и место установки. Сравните габариты, крепление и характеристики на странице товара.",
                 "Չափեք առաստաղի բարձրությունն ու տեղադրման հատվածը։ Համեմատեք ապրանքի էջի չափերը, ամրացումն ու բնութագրերը։",
                 "Measure the ceiling height and installation area. Compare dimensions, mounting and specifications on the product page.") + actions((("catalog", "Каталог"), ("compare", "Сравнение")))) +
          card("spark", t("Примерьте перед выбором", "Փորձեք նախքան ընտրելը", "Preview before choosing"),
               p("Загрузите фото в Lusar AI. Визуализация помогает оценить форму и сочетания; точные размеры и световой расчёт она не заменяет.",
                 "Վերբեռնեք լուսանկարը Lusar AI-ում։ Պատկերավորումն օգնում է գնահատել ձևն ու համադրությունը, սակայն չի փոխարինում ճշգրիտ չափումներին և լուսային հաշվարկին։",
                 "Upload a photo to Lusar AI to explore shapes and combinations. A preview does not replace measurements or a lighting calculation.") + actions((("ai", "Lusar AI"),))) + '</div>',
          description="Подбор света по комнате и задачам: размеры, характеристики, сравнение и примерка с Lusar AI.")

    write("services", "Услуги LUSAR", '<div class="info-cards">' +
          card("search", t("Выбор и сравнение", "Ընտրություն և համեմատում", "Explore and compare"),
               p("Фильтруйте каталог, сравнивайте характеристики и сохраняйте понравившиеся модели в избранное.",
                 "Զտեք կատալոգը, համեմատեք բնութագրերը և պահպանեք հավանած մոդելները նախընտրածներում։",
                 "Filter the catalogue, compare specifications and save your favourite models.") + actions((("selection", "Подбор освещения"), ("catalog", "Каталог"))), featured=True) +
          card("spark", "Lusar AI", p("Примерьте выбранные светильники на фотографии своей комнаты на сайте или в Lusar AI Bot.",
                 "Փորձեք ընտրված լուսատուները ձեր սենյակի լուսանկարում՝ կայքում կամ Lusar AI Bot-ում։",
                 "Preview selected lights in a photo of your room on the website or in Lusar AI Bot.") + actions((("ai", "Начать примерку"),))) +
          card("orders", t("Сопровождение заявки", "Հայտի ուղեկցում", "Help with your request"),
               p("Отправьте заявку без онлайн-оплаты. Менеджер уточнит наличие, итоговую сумму и способ получения.",
                 "Ուղարկեք հայտը՝ առանց առցանց վճարման։ Մենեջերը կճշտի առկայությունը, վերջնական գումարը և ստացման եղանակը։",
                 "Send a request without online payment. A manager will confirm availability, the final amount and collection or delivery.") + actions((("support", "Поддержка"), ("order-status", "Статус заявки")))) + '</div>',
          description="Инструменты LUSAR: подбор и сравнение светильников, примерка с AI и помощь по заявке.")

    write("professionals/request", "Запрос на проект", '<div class="info-cards info-cards-pair">' +
          card("desk", t("Подготовьте детали", "Պատրաստեք մանրամասները", "Prepare the details"),
               p("Для предметного разговора подготовьте план или фото, размеры помещения, зоны освещения, количество светильников и желаемые сроки.",
                 "Քննարկման համար պատրաստեք հատակագիծը կամ լուսանկարը, տարածքի չափերը, լուսավորման գոտիները, լուսատուների քանակը և ցանկալի ժամկետները։",
                 "Have a plan or photo, room dimensions, lighting zones, quantities and preferred dates ready for the discussion.") + actions((("favorites", "Избранное"), ("selection", "Подбор освещения"))), featured=True) +
          card("phone", t("Обсудите с менеджером", "Քննարկեք մենեջերի հետ", "Talk to a manager"),
               p("Позвоните, чтобы уточнить возможности под ваш проект. Состав предложения, наличие и условия согласуются индивидуально.",
                 "Զանգահարեք՝ ձեր նախագծի հնարավորությունները ճշտելու համար։ Առաջարկը, առկայությունն ու պայմանները համաձայնեցվում են անհատապես։",
                 "Call to discuss your project. The proposal, availability and terms are agreed individually.") +
               '<a class="contact-phone" href="tel:+37477123451">+374 77 123451</a>' + actions((("contacts", "Контакты"),))) + '</div>',
          description="Что подготовить для обсуждения освещения проекта с менеджером LUSAR: план, размеры, зоны и модели.")

    write("account/notifications", "Уведомления", '<div class="info-cards info-cards-pair">' +
          card("orders", t("Следите за заявкой", "Հետևեք ձեր հայտին", "Track your request"),
               p("Актуальный статус доступен в разделе «Мои заказы». Для гостевой заявки используйте приватную ссылку, выданную после оформления.",
                 "Ընթացիկ կարգավիճակը հասանելի է «Իմ պատվերները» բաժնում։ Առանց հաշվի հայտի համար օգտագործեք ձևակերպումից հետո ստացած մասնավոր հղումը։",
                 "See the current status in My orders. For a guest request, use the private link provided after submission.") + actions((("account/orders", "Мои заказы"), ("order-status", "Статус заявки"))), featured=True) +
          card("phone", t("Связь по заказу", "Կապ պատվերի վերաբերյալ", "Contact about an order"),
               p("Менеджер использует контактные данные из заявки для подтверждения деталей. Автоматическая клиентская рассылка и push-уведомления пока не подключены.",
                 "Մենեջերն օգտագործում է հայտի կոնտակտները՝ մանրամասները հաստատելու համար։ Հաճախորդների ավտոմատ նամակներն ու push-ծանուցումները դեռ միացված չեն։",
                 "A manager uses your request's contact details to confirm the order. Automated customer emails and push notifications are not connected yet.") + actions((("support", "Поддержка"), ("account/settings", "Профиль")))) + '</div>', draft=True)

    write("legal/loyalty", "Условия акций и скидок", '<div class="info-cards">' +
          card("spark", t("Накопительная скидка", "Կուտակային զեղչ", "Loyalty discount"),
               p("Учитываются выполненные и оплаченные заказы после скидок. Возвраты уменьшают накопления. Текущий уровень виден в кабинете.",
                 "Հաշվարկվում են կատարված և վճարված պատվերները՝ զեղչերից հետո։ Վերադարձները նվազեցնում են կուտակումները։ Ընթացիկ մակարդակը տեսանելի է անձնական էջում։",
                 "Completed and paid orders count after discounts. Returns reduce qualifying spend. See your current level in your account.") +
               '<dl class="loyalty-thresholds">' + ''.join(f'<dt>{threshold:,} ֏</dt><dd>{percent}%</dd>'.replace(',', ' ') for threshold, percent in LOYALTY_TIERS) + '</dl>' + actions((("account/loyalty", "Мои скидки"),)), featured=True) +
          card("orders", t("Первая покупка и промокоды", "Առաջին գնում և պրոմոկոդեր", "First purchase and promo codes"),
               p("Пока акция активна, зарегистрированному покупателю без выполненных заказов доступно 10% на первый заказ. Эта скидка применяется отдельно. Персональная скидка может сочетаться с одним промокодом; промокод уменьшает остаток не более чем на 20%.",
                 "Ակցիայի ընթացքում կատարված պատվերներ չունեցող գրանցված գնորդին հասանելի է առաջին պատվերի 10% զեղչը։ Այն կիրառվում է առանձին։ Անձնական զեղչը կարող է համադրվել մեկ պրոմոկոդի հետ, որը մնացորդը նվազեցնում է առավելագույնը 20%-ով։",
                 "While the offer is active, registered customers with no completed orders can get 10% off their first order. It applies separately. A personal discount can combine with one promo code, which reduces the remaining amount by at most 20%.") + actions((("offers", "Акции"),))) +
          card("check", t("Скидка ко дню рождения", "Ծննդյան օրվա զեղչ", "Birthday discount"),
               p("Промокод Happy даёт предварительную скидку 10% независимо от регистра букв. До оплаты менеджер должен подтвердить право на акцию. Подтверждающие документы на сайте не загружаются.",
                 "Happy պրոմոկոդը տալիս է նախնական 10% զեղչ՝ անկախ մեծատառերից ու փոքրատառերից։ Մինչև վճարումը մենեջերը պետք է հաստատի ակցիայից օգտվելու իրավունքը։ Հաստատող փաստաթղթեր կայքում չեն վերբեռնվում։",
                 "Happy gives a preliminary 10% discount, regardless of letter case. A manager must confirm eligibility before payment. Supporting documents are not uploaded on this website.") + actions((("support", "Поддержка"),))) + '</div>', draft=True)

    write("legal/cookies", "Политика cookie", '<div class="info-cards">' +
          card("account", t("Вход и безопасность", "Մուտք և անվտանգություն", "Sign-in and security"),
               p("Защищённая cookie входа действует до 7 дней. Временная cookie для проверки входа — до 10 минут. Они недоступны JavaScript и нужны для работы кабинета.",
                 "Պաշտպանված մուտքի cookie-ն գործում է մինչև 7 օր, իսկ մուտքի ստուգման ժամանակավոր cookie-ն՝ մինչև 10 րոպե։ JavaScript-ը դրանց հասանելիություն չունի․ դրանք անհրաժեշտ են անձնական էջի համար։",
                 "The secure sign-in cookie lasts up to 7 days; the temporary login-check cookie lasts up to 10 minutes. JavaScript cannot read them. They are needed for your account.") , featured=True) +
          card("overview", t("Настройки в браузере", "Դիտարկիչի կարգավորումներ", "Browser preferences"),
               p("Язык, тема, корзина, избранное, сравнение и выбор статистики сохраняются в локальном хранилище браузера. Их можно удалить через настройки браузера; локальные предпочтения при этом сбросятся.",
                 "Լեզուն, թեման, զամբյուղը, նախընտրածները, համեմատումը և վիճակագրության ընտրությունը պահվում են դիտարկիչում։ Դրանք կարող եք ջնջել դիտարկիչի կարգավորումներում․ տեղական նախընտրությունները կզրոյացվեն։",
                 "Language, theme, bag, wishlist, comparison and your statistics choice are saved in browser storage. Clearing site data in your browser resets those local preferences.")) +
          card("filter", t("Статистика по вашему выбору", "Վիճակագրություն՝ ձեր ընտրությամբ", "Optional statistics"),
               p("Google Analytics и Яндекс Метрика запускаются после разрешения статистики. Изменить выбор можно через «Настройки cookie» внизу любой страницы. Отключение останавливает дальнейший сбор на сайте, но не удаляет уже переданные сведения у провайдеров.",
                 "Google Analytics-ը և Յանդեքս Մետրիկան գործարկվում են վիճակագրությունը թույլատրելուց հետո։ Ընտրությունը փոխեք ցանկացած էջի ներքևի cookie-ի կարգավորումներում։ Անջատումը դադարեցնում է հետագա հավաքումը, բայց չի ջնջում մատակարարներին արդեն փոխանցված տվյալները։",
                 "Google Analytics and Yandex Metrica start after you allow statistics. Change your choice using Cookie settings at the bottom of any page. Disabling stops further collection here; it does not erase information already sent to providers.")) +
          '</div>' + actions((("legal/privacy", "Политика конфиденциальности"), ("contacts", "Контакты"))), draft=True)
