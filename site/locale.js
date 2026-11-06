(() => {
  const translations = {
    "Мои заказы": ["Իմ պատվերները", "My orders"],
    "Мои скидки": ["Իմ զեղչերը", "My discounts"],
    "Профиль": ["Պրոֆիլ", "Profile"],
    "Обзор": ["Ակնարկ", "Overview"],
    "Вход в LUSAR": ["Մուտք LUSAR", "Sign in to LUSAR"],
    "Регистрация": ["Գրանցում", "Register"],
    "Восстановление доступа": ["Մուտքի վերականգնում", "Recover access"],
    "Загружаем кабинет…": ["Բեռնում ենք անձնական էջը…", "Loading your account…"],
    "Ваш свет. Ваши привилегии.": ["Ձեր լույսը։ Ձեր առավելությունները։", "Your light. Your privileges."],
    "Заказы, адреса и скидки — в одном месте.": ["Պատվերներ, հասցեներ և զեղչեր՝ մեկ վայրում։", "Orders, addresses and discounts in one place."],
    "История ваших заявок": ["Ձեր հայտերի պատմությունը", "Your order history"],
    "Сохранённая корзина и избранное": ["Պահպանված զամբյուղ և նախընտրածներ", "Saved bag and wishlist"],
    "Скидки за выполненные заказы": ["Զեղչեր կատարված պատվերների համար", "Discounts for completed orders"],
    "Войти в LUSAR": ["Մուտք գործել LUSAR", "Sign in to LUSAR"],
    "Продолжить с Google": ["Շարունակել Google-ով", "Continue with Google"],
    "Войти по email": ["Մուտք էլ. փոստով", "Sign in with email"],
    "Создать аккаунт": ["Ստեղծել հաշիվ", "Create an account"],
    "Продолжить без входа": ["Շարունակել առանց մուտքի", "Continue as a guest"],
    "Вход пока не подключён. Страница в разработке.": ["Մուտքը դեռ միացված չէ։ Էջը մշակման փուլում է։", "Sign-in is not connected yet. Page in development."],
    "На странице входа выберите «Не помню пароль» и следуйте инструкции в письме.": ["Մուտքի էջում ընտրեք «Չեմ հիշում գաղտնաբառը» և հետևեք նամակի հրահանգներին։", "On the sign-in page choose “Forgot password” and follow the email instructions."],
    "Разделы личного кабинета": ["Անձնական էջի բաժիններ", "Account sections"],
    "Выйти": ["Դուրս գալ", "Sign out"],
    "Последние заказы": ["Վերջին պատվերները", "Recent orders"],
    "Все заказы": ["Բոլոր պատվերները", "All orders"],
    "Показать ещё": ["Ցույց տալ ավելին", "Show more"],
    "Добавить адрес": ["Ավելացնել հասցե", "Add an address"],
    "Название адреса": ["Հասցեի անունը", "Address label"],
    "Например, дом": ["Օրինակ՝ տուն", "For example, home"],
    "Адрес": ["Հասցե", "Address"],
    "Сохранить адрес": ["Պահպանել հասցեն", "Save address"],
    "Отменить": ["Չեղարկել", "Cancel"],
    "Контактные данные": ["Կոնտակտային տվյալներ", "Contact details"],
    "Email": ["Էլ. փոստ", "Email"],
    "Сохранить изменения": ["Պահպանել փոփոխությունները", "Save changes"],
    "Email подтверждается при входе. Для смены пароля откройте восстановление доступа.": ["Էլ. փոստը հաստատվում է մուտքի ժամանակ։ Գաղտնաբառը փոխելու համար բացեք մուտքի վերականգնումը։", "Email is verified when you sign in. Use access recovery to change your password."],
    "Накопления бессрочные.": ["Կուտակումներն անժամկետ են։", "Your qualifying spend does not expire."],
    "Учитываются выполненные и оплаченные заказы после скидок. При возврате накопления пересчитываются.": ["Հաշվարկվում են կատարված և վճարված պատվերները՝ զեղչերից հետո։ Վերադարձի դեպքում կուտակումները վերահաշվարկվում են։", "Completed, paid orders count after discounts. Returns adjust your qualifying spend."],
    "Ваша скидка": ["Ձեր զեղչը", "Your discount"],
    "Накоплено": ["Կուտակված է", "Qualifying spend"],
    "До следующего уровня": ["Մինչև հաջորդ մակարդակ", "To the next level"],
    "Прогресс скидки": ["Զեղչի առաջընթաց", "Discount progress"],
    "У вас максимальная скидка.": ["Դուք ունեք առավելագույն զեղչը։", "You have reached the highest discount."],
    "Доступна при оформлении. Применяется отдельно от других скидок и промокодов.": ["Հասանելի է պատվերի ձևակերպման ժամանակ։ Կիրառվում է այլ զեղչերից և պրոմոկոդերից առանձին։", "Available at checkout, separately from other discounts and promo codes."],
    "Скидка закреплена за вашей текущей заявкой.": ["Զեղչը ամրագրված է ձեր ընթացիկ հայտին։", "This discount is reserved for your current order request."],
    "Предложение уже использовано.": ["Առաջարկն արդեն օգտագործված է։", "This offer has already been used."],
    "Новая заявка": ["Նոր հայտ", "New request"],
    "В процессе": ["Ընթացքում", "In progress"],
    "Выполнено": ["Կատարված է", "Completed"],
    "Отменено": ["Չեղարկված է", "Cancelled"],
    "Сумма заказа": ["Պատվերի գումարը", "Order total"],
    "Итог после возврата": ["Գումարը վերադարձից հետո", "Total after returns"],
    "Оплата отмечена менеджером.": ["Վճարումը նշված է մենեջերի կողմից։", "Payment recorded by your manager."],
    "У вас пока нет заказов.": ["Դուք դեռ պատվերներ չունեք։", "You have no orders yet."],
    "Сохранённых адресов пока нет.": ["Պահպանված հասցեներ դեռ չկան։", "No saved addresses yet."],
    "Основной адрес": ["Հիմնական հասցե", "Default address"],
    "Изменить": ["Փոխել", "Edit"],
    "Изменить адрес": ["Փոխել հասցեն", "Edit address"],
    "Сделать основным": ["Դարձնել հիմնական", "Make default"],
    "Адреса обновлены.": ["Հասցեները թարմացված են։", "Addresses updated."],
    "Адрес сохранён.": ["Հասցեն պահպանված է։", "Address saved."],
    "Изменения сохранены.": ["Փոփոխությունները պահպանված են։", "Changes saved."],
    "Добро пожаловать": ["Բարի գալուստ", "Welcome"],
    "Скидка кабинета": ["Անձնական էջի զեղչ", "Account discount"],
    "Скидка на первый заказ": ["Առաջին պատվերի զեղչ", "First-order discount"],
    "Выберите скидку": ["Ընտրեք զեղչը", "Choose a discount"],
    "Только промокод": ["Միայն պրոմոկոդ", "Promo code only"],
    "Скидка кабинета и промокод": ["Անձնական էջի զեղչ և պրոմոկոդ", "Account discount and promo code"],
    "Скидка на первый заказ применяется отдельно.": ["Առաջին պատվերի զեղչը կիրառվում է առանձին։", "The first-order discount applies separately."],
    "Из личного кабинета": ["Անձնական էջից", "From your account"],
    "Войти и использовать скидку кабинета": ["Մուտք գործել և օգտվել անձնական զեղչից", "Sign in to use your account discount"],
    "Подтвердите email в письме и повторите вход.": ["Հաստատեք էլ. փոստը նամակում և կրկին մուտք գործեք։", "Verify your email using the message, then sign in again."],
    "Вход не подтверждён. Повторите попытку.": ["Մուտքը չի հաստատվել։ Կրկին փորձեք։", "Sign-in could not be confirmed. Please try again."],
    "Личный кабинет временно недоступен. Попробуйте позже.": ["Անձնական էջը ժամանակավորապես անհասանելի է։ Փորձեք ավելի ուշ։", "Your account is temporarily unavailable. Please try again later."],
    "Войдите в личный кабинет.": ["Մուտք գործեք անձնական էջ։", "Please sign in to your account."],
    "Не удалось сохранить изменения.": ["Չհաջողվեց պահպանել փոփոխությունները։", "Could not save changes."],
    "Обновите страницу и повторите действие.": ["Թարմացրեք էջը և կրկնեք գործողությունը։", "Refresh the page and try again."],
    "Корзина изменилась в другом устройстве. Обновите страницу.": ["Զամբյուղը փոխվել է այլ սարքում։ Թարմացրեք էջը։", "Your bag changed on another device. Please refresh the page."],
    "Браузер не сохранил корзину. Проверьте настройки хранения данных.": ["Դիտարկիչը չի պահպանել զամբյուղը։ Ստուգեք տվյալների պահպանման կարգավորումները։", "Your browser could not save your bag. Check its storage settings."],
    "Подбор светильников": ["Լուսատուների ընտրություն", "Find lighting"],
    "Название или артикул": ["Անվանում կամ արտիկուլ", "Name or SKU"],
    "Закрыть уведомление": ["Փակել ծանուցումը", "Dismiss notification"],
    "Фильтры": ["Զտիչներ", "Filters"],
    "Сбросить фильтры": ["Մաքրել զտիչները", "Clear filters"],
    "Тип светильника": ["Լուսատուի տեսակ", "Light type"],
    "Цена от, ֏": ["Նվազագույն գին, ֏", "Minimum price, ֏"],
    "Все": ["Բոլորը", "All"],
    "Температура света": ["Լույսի ջերմաստիճան", "Light temperature"],
    "Ничего не найдено": ["Ոչինչ չի գտնվել", "No matches"],
    "Попробуйте изменить запрос или сбросить фильтры.": ["Փորձեք փոխել հարցումը կամ մաքրել զտիչները։", "Try a different search or clear the filters."],
    "Категории": ["Բաժիններ", "Categories"],
    "Предыдущее фото": ["Նախորդ լուսանկարը", "Previous photo"],
    "Следующее фото": ["Հաջորդ լուսանկարը", "Next photo"],
    "Увеличить фото": ["Մեծացնել լուսանկարը", "Enlarge photo"],
    "Фотографии товара": ["Ապրանքի լուսանկարներ", "Product photos"],
    "Увеличенное фото товара": ["Ապրանքի մեծացված լուսանկարը", "Enlarged product photo"],
    "В этой категории": ["Այս բաժնում", "In this category"],
    "Все модели": ["Բոլոր մոդելները", "All models"],
    "Цоколь": ["Կոթառ", "Socket"],
    "Мощность": ["Հզորություն", "Wattage"],
    "Цветовая температура": ["Գունային ջերմաստիճան", "Color temperature"],
    "Защита IP": ["IP պաշտպանություն", "IP rating"],
    "Диаметр": ["Տրամագիծ", "Diameter"],
    "Источник света": ["Լույսի աղբյուր", "Light source"],
    "Напряжение питания": ["Սնուցման լարում", "Voltage"],
    "Количество ламп": ["Լամպերի քանակ", "Number of lamps"],
    "Цвет корпуса": ["Կորպուսի գույն", "Finish"],
    "Материал": ["Նյութ", "Material"],
    "Высота": ["Բարձրություն", "Height"],
    "Ширина": ["Լայնություն", "Width"],
    "Глубина": ["Խորություն", "Depth"],
    "Длина подвеса": ["Կախոցի երկարություն", "Suspension length"],
    "Световой поток": ["Լուսային հոսք", "Luminous flux"],
    "Цвет свечения": ["Լույսի գույն", "Light color"],
    "Индекс цветопередачи CRI / Ra": ["Գունափոխանցման ինդեքս CRI / Ra", "Color rendering index CRI / Ra"],
    "Угол рассеивания": ["Ճառագայթի անկյուն", "Beam angle"],
    "Регулируемая высота": ["Կարգավորվող բարձրություն", "Adjustable height"],
    "Каталог": ["Կատալոգ", "Catalog"],
    "По комнатам": ["Ըստ սենյակի", "By room"],
    "Контакты": ["Կապ", "Contact"],
    "Поиск": ["Որոնում", "Search"],
    "Избранное": ["Նախընտրածներ", "Wishlist"],
    "Личный кабинет": ["Անձնական էջ", "Account"],
    "Этапы заявки": ["Հայտի փուլեր", "Order steps"],
    "Подтверждение": ["Հաստատում", "Confirmation"],
    "Товары в корзине": ["Ապրանքները զամբյուղում", "Items in your bag"],
    "Товары в заявке": ["Հայտի ապրանքները", "Order items"],
    "Товары": ["Ապրանքներ", "Items"],
    "Цена за штуку": ["Մեկ հատի գինը", "Unit price"],
    "Уменьшить количество": ["Նվազեցնել քանակը", "Decrease quantity"],
    "Увеличить количество": ["Ավելացնել քանակը", "Increase quantity"],
    "Удалить из корзины": ["Հեռացնել զամբյուղից", "Remove from bag"],
    "Ваш заказ": ["Ձեր պատվերը", "Your order"],
    "Скидка по промокоду": ["Զեղչ պրոմոկոդով", "Promo discount"],
    "Предварительный итог": ["Նախնական գումար", "Estimated total"],
    "Введите промокод": ["Մուտքագրեք պրոմոկոդը", "Enter promo code"],
    "Промокод применён.": ["Պրոմոկոդը կիրառված է։", "Promo code applied."],
    "Оплата после подтверждения.": ["Վճարում՝ հաստատումից հետո։", "Payment after confirmation."],
    "Наличие, доставку и итоговую сумму уточнит менеджер.": ["Մենեջերը կճշտի առկայությունը, առաքումը և վերջնական գումարը։", "Your manager will confirm availability, delivery and the total."],
    "Способы оплаты": ["Վճարման եղանակներ", "Payment options"],
    "Найдите свет для вашего пространства.": ["Գտեք լույս ձեր տարածքի համար։", "Find the light for your space."],
    "← Продолжить покупки": ["← Շարունակել գնումները", "← Continue shopping"],
    "← Вернуться в корзину": ["← Վերադառնալ զամբյուղ", "← Back to bag"],
    "Без регистрации": ["Առանց գրանցման", "Guest checkout"],
    "Как с вами связаться": ["Ինչպե՞ս կապվել ձեզ հետ", "How to reach you"],
    "Укажите имя и телефон. Остальное — по желанию.": ["Նշեք անունը և հեռախոսը։ Մնացածը՝ ըստ ցանկության։", "Enter your name and phone. Everything else is optional."],
    "Ваше имя": ["Ձեր անունը", "Your name"],
    "Позвоним, чтобы подтвердить заявку.": ["Կզանգենք՝ հայտը հաստատելու համար։", "We will call to confirm your request."],
    "Email и адрес (необязательно)": ["Էլ. փոստ և հասցե (ոչ պարտադիր)", "Email and address (optional)"],
    "Город, улица, дом": ["Քաղաք, փողոց, շենք", "City, street, building"],
    "Менеджер подтвердит цену и скидку по этой заявке.": ["Մենեջերը կհաստատի այս հայտի գինն ու զեղչը։", "Your manager will confirm the price and discount for this request."],
    "Проверьте имя и номер телефона.": ["Ստուգեք անունը և հեռախոսահամարը։", "Check your name and phone number."],
    "Отправляем заявку…": ["Ուղարկում ենք հայտը…", "Sending your request…"],
    "Номер заявки": ["Հայտի համարը", "Request number"],
    "Каталог обновлён. Проверьте состав и сумму заявки.": ["Կատալոգը թարմացված է։ Ստուգեք հայտի ապրանքներն ու գումարը։", "The catalog has changed. Review your items and total."],
    "Каталог временно недоступен для проверки. Попробуйте отправить заявку позже.": ["Կատալոգը ժամանակավորապես հնարավոր չէ ստուգել։ Փորձեք հայտը ուղարկել ավելի ուշ։", "The catalog cannot be checked right now. Please submit your request later."],
    "Заявка принята": ["Հայտն ընդունված է", "Request received"],
    "Менеджер свяжется с вами в ближайшее время.": ["Մենեջերը շուտով կկապվի ձեզ հետ։", "Your manager will contact you shortly."],
    "При звонке назовите номер заявки.": ["Զանգելիս նշեք հայտի համարը։", "Please quote your request number when calling."],
    "Здесь появится номер после отправки заявки.": ["Հայտն ուղարկելուց հետո համարն այստեղ կհայտնվի։", "Your number will appear here after you submit a request."],
    "Не удалось изменить количество.": ["Չհաջողվեց փոխել քանակը։", "Could not update the quantity."],
    "Не удалось обновить корзину.": ["Չհաջողվեց թարմացնել զամբյուղը։", "Could not update your bag."],
    "Максимальное количество — 999.": ["Առավելագույն քանակը՝ 999։", "The maximum quantity is 999."],
    "Корзина": ["Զամբյուղ", "Bag"],
    "Сравнение": ["Համեմատություն", "Compare"],
    "Меню": ["Մենյու", "Menu"],
    "LUSAR — главная": ["LUSAR — գլխավոր", "LUSAR — home"],
    "Язык сайта": ["Կայքի լեզուն", "Site language"],
    "Светлая тема": ["Լուսավոր թեմա", "Light mode"],
    "Тёмная тема": ["Մուգ թեմա", "Dark mode"],
    "Основная навигация": ["Հիմնական մենյու", "Main navigation"],
    "Поиск и покупки": ["Որոնում և գնումներ", "Search and shopping"],
    "К содержанию": ["Անցնել բովանդակությանը", "Skip to content"],
    "Весь каталог": ["Ամբողջ կատալոգը", "View catalog"],
    "Все комнаты": ["Բոլոր սենյակները", "All rooms"],
    "Свет для жизни": ["Լույս՝ կյանքի համար", "Light for living"],
    "Светильники для дома и проектов.": ["Լուսատուներ տան և նախագծերի համար։", "Lighting for homes and projects."],
    "Открыть каталог": ["Բացել կատալոգը", "Explore the catalog"],
    "Примерить с Lusar AI": ["Փորձել Lusar AI-ով", "Try with Lusar AI"],
    "Выберите свой свет": ["Ընտրեք ձեր լույսը", "Find your light"],
    "Из каталога": ["Կատալոգից", "From the catalog"],
    "Все светильники": ["Բոլոր լուսատուները", "All lighting"],
    "Свет по комнатам": ["Լույս՝ ըստ սենյակի", "Lighting by room"],
    "Пример интерьера": ["Ինտերիերի օրինակ", "Illustrative interior"],
    "Ваш интерьер. Новый свет.": ["Ձեր ինտերիերը։ Նոր լույս։", "Your space. A new light."],
    "Загрузите фото комнаты и примерьте светильники из каталога.": ["Վերբեռնեք սենյակի լուսանկարը և փորձեք կատալոգի լուսատուները։", "Upload a room photo and try lighting from the catalog."],
    "Начать примерку": ["Սկսել փորձարկումը", "Start visualizing"],
    "О светильнике": ["Լուսատուի մասին", "About this light"],
    "Характеристики": ["Բնութագրեր", "Specifications"],
    "В избранное": ["Նախընտրածներում", "Save to wishlist"],
    "Сравнить": ["Համեմատել", "Compare"],
    "Открыть сравнение": ["Բացել համեմատությունը", "View comparison"],
    "Перейти в корзину": ["Անցնել զամբյուղ", "Go to bag"],
    "Примерить в моей комнате": ["Փորձել իմ սենյակում", "Visualize in my room"],
    "Посмотрите, как светильник впишется в ваш интерьер.": ["Տեսեք՝ ինչպես լուսատուն կհամապատասխանի ձեր ինտերիերին։", "See how this light fits your space."],
    "Уточнить по товару": ["Ճշտել ապրանքի մասին", "Ask about this light"],
    "Навигация по каталогу": ["Կատալոգի նավարկում", "Catalog navigation"],
    "Сценарий освещения": ["Լուսավորության սցենար", "Lighting scene"],
    "День": ["Ցերեկ", "Day"],
    "Тёплый": ["Ջերմ", "Warm"],
    "Вечер": ["Երեկո", "Evening"],
    "Тёплый свет над столом": ["Ջերմ լույս սեղանի վերևում", "Warm light above the table"],
    "Дневной свет из окна": ["Ցերեկային լույս պատուհանից", "Daylight from the window"],
    "Мягкий свет в полутени": ["Մեղմ լույս կիսաստվերում", "Soft light in the evening"],
    "Выбор света": ["Լույսի ընտրություն", "Explore"],
    "Покупателям": ["Գնորդներին", "Customer care"],
    "О LUSAR": ["LUSAR-ի մասին", "About LUSAR"],
    "Бренды": ["Ապրանքանիշեր", "Brands"],
    "Статьи": ["Հոդվածներ", "Journal"],
    "Акции": ["Առաջարկներ", "Offers"],
    "Доставка": ["Առաքում", "Delivery"],
    "Оплата": ["Վճարում", "Payment"],
    "Выберите удобный способ оплаты при подтверждении заказа.": ["Պատվերը հաստատելիս ընտրեք վճարման հարմար եղանակը։", "Choose your preferred payment method when confirming your order."],
    "В магазине": ["Խանութում", "In store"],
    "После подтверждения заказа менеджером.": ["Մենեջերի կողմից պատվերը հաստատելուց հետո։", "After your manager confirms the order."],
    "По чеку менеджера": ["Մենեջերի ուղարկած հաշվով", "Using the manager's payment slip"],
    "Менеджер пришлёт данные для оплаты.": ["Մենեջերը կուղարկի վճարման տվյալները։", "Your manager will send the payment details."],
    "При получении": ["Ստանալիս", "On receipt"],
    "Способ оплаты согласует менеджер.": ["Վճարման եղանակը կհամաձայնեցնի մենեջերը։", "Your manager will confirm the payment method."],
    "Ждём вас в наших магазинах в Ереване.": ["Սպասում ենք ձեզ Երևանի մեր խանութներում։", "Visit our stores in Yerevan."],
    "Как добраться": ["Ինչպես հասնել", "Get directions"],
    "На связи": ["Կապ մեզ հետ", "Get in touch"],
    "Поможем с заказом и выбором света.": ["Կօգնենք պատվերի և լույսի ընտրության հարցում։", "We can help with your order and lighting choices."],
    "Задать вопрос": ["Հարց տալ", "Ask a question"],
    "Гарантия и возврат": ["Երաշխիք և վերադարձ", "Warranty and returns"],
    "Частые вопросы": ["Հաճախ տրվող հարցեր", "FAQ"],
    "Поддержка": ["Աջակցություն", "Support"],
    "О нас": ["Մեր մասին", "About us"],
    "Наши партнёры": ["Մեր գործընկերները", "Our partners"],
    "Новости": ["Նորություններ", "News"],
    "Правовая информация": ["Իրավական տեղեկություն", "Legal information"],
    "Карта сайта": ["Կայքի քարտեզ", "Sitemap"],
    "Настройки cookie": ["Cookie-ի կարգավորումներ", "Cookie settings"],
    "Только необходимые": ["Միայն անհրաժեշտները", "Essential only"],
    "Разрешить статистику": ["Թույլատրել վիճակագրությունը", "Allow analytics"],
    "Подробнее о cookie": ["Ավելին cookie-ի մասին", "About cookies"],
    "Браузер хранит настройки сайта и корзину. Сбор статистики можно разрешить или отключить отдельно.": [
      "Դիտարկիչը պահում է կայքի կարգավորումներն ու զամբյուղը։ Վիճակագրության հավաքումը կարող եք թույլատրել կամ անջատել առանձին։",
      "Your browser stores site preferences and your bag. You can allow or disable analytics separately."
    ],
    "Люстры": ["Ջահեր", "Chandeliers"],
    "Подвесы": ["Կախովի լուսատուներ", "Pendants"],
    "Подвесные светильники": ["Կախովի լուսատուներ", "Pendant lights"],
    "Бра": ["Պատի լուսատուներ", "Wall lights"],
    "Прожекторы": ["Լուսարձակներ", "Floodlights"],
    "Уличный свет": ["Արտաքին լուսավորություն", "Outdoor lighting"],
    "Уличное освещение": ["Արտաքին լուսավորություն", "Outdoor lighting"],
    "Гостиная": ["Հյուրասենյակ", "Living room"],
    "Спальня": ["Ննջասենյակ", "Bedroom"],
    "Кухня и столовая": ["Խոհանոց և ճաշասենյակ", "Kitchen and dining"],
    "Рабочая зона": ["Աշխատանքային գոտի", "Workspace"],
    "Улица и терраса": ["Բակ և տեռասա", "Outdoors and terrace"],
    "Каталог освещения": ["Լուսավորության կատալոգ", "Lighting catalog"],
    "К товарам": ["Դիտել ապրանքները", "View products"],
    "Все категории": ["Բոլոր բաժինները", "All categories"],
    "Подкатегории": ["Ենթաբաժիններ", "Subcategories"],
    "Цена до, ֏": ["Առավելագույն գին, ֏", "Maximum price, ֏"],
    "Сортировка": ["Տեսակավորում", "Sort by"],
    "Как в каталоге": ["Ըստ կատալոգի", "Featured"],
    "Сначала дешевле": ["Սկզբում՝ մատչելիները", "Price low to high"],
    "Сначала дороже": ["Սկզբում՝ թանկերը", "Price high to low"],
    "Сбросить": ["Մաքրել", "Reset"],
    "По выбранной цене товаров нет.": ["Այս գնով ապրանքներ չկան։", "No products at this price."],
    "Цена по запросу": ["Գինը՝ հարցմամբ", "Price on request"],
    "Наличие уточнит менеджер.": ["Առկայությունը կճշտի մենեջերը։", "Your manager will confirm availability."],
    "Добавить в корзину": ["Ավելացնել զամբյուղում", "Add to bag"],
    "Добавить в избранное": ["Ավելացնել նախընտրածներում", "Add to wishlist"],
    "Добавить к сравнению": ["Ավելացնել համեմատությանը", "Add to comparison"],
    "Открыть корзину": ["Բացել զամբյուղը", "View bag"],
    "Продолжить покупки": ["Շարունակել գնումները", "Continue shopping"],
    "Оформить заявку": ["Ուղարկել հայտ", "Request an order"],
    "Оформление заявки": ["Պատվերի հայտ", "Order request"],
    "Отправить заявку": ["Ուղարկել հայտը", "Send request"],
    "Количество": ["Քանակ", "Quantity"],
    "Удалить": ["Հեռացնել", "Remove"],
    "Удалить недоступный товар": ["Հեռացնել անհասանելի ապրանքը", "Remove unavailable product"],
    "Товар снят с публикации или сейчас недоступен.": ["Ապրանքն այլևս հրապարակված չէ կամ այժմ հասանելի չէ։", "This product is no longer listed or is currently unavailable."],
    "Уберите недоступные товары, чтобы оформить заявку.": ["Հայտն ուղարկելու համար հեռացրեք անհասանելի ապրանքները։", "Remove unavailable products to request an order."],
    "Корзина пока пуста.": ["Զամբյուղը դեռ դատարկ է։", "Your bag is empty."],
    "Итоговую сумму подтвердит менеджер.": ["Վերջնական գումարը կհաստատի մենեջերը։", "Your manager will confirm the total."],
    "Имя": ["Անուն", "Name"],
    "Телефон": ["Հեռախոս", "Phone"],
    "Email (необязательно)": ["Էլ. փոստ (ոչ պարտադիր)", "Email (optional)"],
    "Адрес (необязательно)": ["Հասցե (ոչ պարտադիր)", "Address (optional)"],
    "Промокод": ["Պրոմոկոդ", "Promo code"],
    "Промокод не найден.": ["Պրոմոկոդը չի գտնվել։", "Promo code not found."],
    "Менеджер уточнит наличие, итоговую сумму и способ оплаты.": [
      "Մենեջերը կճշտի առկայությունը, վերջնական գումարը և վճարման եղանակը։",
      "Your manager will confirm availability, the total and payment method."
    ],
    "Страница в разработке": ["Էջը մշակման փուլում է", "Page in development"],
    "Страница в разработке.": ["Էջը մշակման փուլում է։", "Page in development."],
    "Страница не найдена": ["Էջը չի գտնվել", "Page not found"],
    "Вернуться в каталог": ["Վերադառնալ կատալոգ", "Back to catalog"],
    "Закрыть": ["Փակել", "Close"],
    "10% на первый заказ": ["10% առաջին պատվերի համար", "10% off your first order"],
    "Посмотреть условия": ["Դիտել պայմանները", "View terms"],
    "Зарегистрируйтесь и получите скидку на первую покупку.": [
      "Գրանցվեք և ստացեք զեղչ առաջին գնումի համար։", "Register for a discount on your first purchase."
    ],
    "Поиск по каталогу": ["Որոնում կատալոգում", "Search the catalog"],
    "Название, артикул или характеристика": ["Անվանում, արտիկուլ կամ բնութագիր", "Name, SKU or specification"],
    "Найти": ["Գտնել", "Search"],
    "Фото комнаты": ["Սենյակի լուսանկար", "Room photo"],
    "Примерьте новый свет": ["Փորձեք նոր լույսը", "Try a new light"],
    "Ваше фото, ваши пожелания и светильники из каталога LUSAR.": ["Ձեր լուսանկարը, ձեր ցանկությունները և LUSAR-ի կատալոգի լուսատուները։", "Your photo, your preferences and lighting from LUSAR."],
    "Ваша комната": ["Ձեր սենյակը", "Your room"],
    "Загрузите фото комнаты": ["Վերբեռնեք սենյակի լուսանկարը", "Upload your room photo"],
    "Выберите файл или перетащите сюда": ["Ընտրեք ֆայլը կամ քաշեք այստեղ", "Choose a file or drag it here"],
    "JPEG, PNG, WebP · до 4 МБ": ["JPEG, PNG, WebP · մինչև 4 ՄԲ", "JPEG, PNG, WebP · up to 4 MB"],
    "Какой свет вам нравится?": ["Ի՞նչ լույս եք նախընտրում", "What light do you like?"],
    "Идеи для примерки": ["Փորձարկման գաղափարներ", "Ideas to try"],
    "Тёплый свет": ["Ջերմ լույս", "Warm light"],
    "Современный стиль": ["Ժամանակակից ոճ", "Modern style"],
    "Мягкое освещение": ["Մեղմ լուսավորություն", "Soft lighting"],
    "Используйте фото без людей и личных данных.": ["Օգտագործեք լուսանկար՝ առանց մարդկանց և անձնական տվյալների։", "Use a photo without people or personal information."],
    "Примерка освещения": ["Լուսավորության փորձարկում", "Lighting visualization"],
    "Ваша примерка": ["Ձեր փորձարկումը", "Your visualization"],
    "Изменить пожелания ↑": ["Փոխել ցանկությունները ↑", "Edit preferences ↑"],
    "Место для вашего интерьера": ["Տեղ՝ ձեր ինտերիերի համար", "A space for your room"],
    "Загрузите фото, чтобы начать примерку.": ["Վերբեռնեք լուսանկարը՝ փորձարկումը սկսելու համար։", "Upload a photo to start visualizing."],
    "До": ["Մինչև", "Before"],
    "После": ["Հետո", "After"],
    "Сравнить до и после": ["Համեմատել մինչ և հետո", "Compare before and after"],
    "Создаём вашу примерку": ["Պատրաստում ենք ձեր փորձարկումը", "Creating your visualization"],
    "Это может занять несколько минут.": ["Սա կարող է տևել մի քանի րոպե։", "This may take a few minutes."],
    "В примерке": ["Փորձարկման մեջ", "In your visualization"],
    "Почему эти светильники": ["Ինչո՞ւ այս լուսատուները", "Why these lights"],
    "Фото готово к отправке.": ["Լուսանկարը պատրաստ է ուղարկման։", "Your photo is ready."],
    "Фото обработано.": ["Լուսանկարը մշակված է։", "Your photo has been processed."],
    "Визуализация готова.": ["Պատկերավորումը պատրաստ է։", "Your visualization is ready."],
    "Обработка не завершилась.": ["Մշակումը չի ավարտվել։", "Processing did not finish."],
    "Выберите JPEG, PNG или WebP размером до 4 МБ.": ["Ընտրեք JPEG, PNG կամ WebP՝ մինչև 4 ՄԲ։", "Choose a JPEG, PNG or WebP up to 4 MB."],
    "Примерка выбранного светильника в вашей комнате.": ["Ընտրված լուսատուի փորձարկում ձեր սենյակում։", "Try your selected light in your room."],
    "Примерить светильник": ["Փորձել լուսատուն", "Visualize this light"],
    "Пожелания": ["Ցանկություններ", "Your preferences"],
    "Подобрать и примерить свет": ["Ընտրել և փորձել լուսավորություն", "Find and visualize lighting"],
    "Lusar AI временно недоступен. Попробуйте позже.": ["Lusar AI-ն ժամանակավորապես անհասանելի է։ Փորձեք ավելի ուշ։", "Lusar AI is temporarily unavailable. Please try again later."],
    "Достигнут часовой лимит примерок. Попробуйте позже.": ["Հասել եք փորձարկումների ժամային սահմանաչափին։ Փորձեք ավելի ուշ։", "The hourly visualization limit has been reached. Please try again later."],
    "Например: тёплый свет над столом": ["Օրինակ՝ ջերմ լույս սեղանի վերևում", "For example, warm light above the table"],
    "Согласен на отправку фото и пожеланий в OpenAI для обработки.": [
      "Համաձայն եմ լուսանկարն ու ցանկություններն ուղարկել OpenAI՝ մշակման համար։",
      "I consent to sending my photo and preferences to OpenAI for processing."
    ],
    "Подобрать свет по комнате": ["Ընտրել լուսավորություն՝ ըստ սենյակի", "Choose lighting by room"],
    "Все помещения": ["Բոլոր սենյակները", "All rooms"],
    "Что посмотреть в каталоге": ["Ինչ դիտել կատալոգում", "Explore in the catalog"],
    "Все бренды": ["Բոլոր ապրանքանիշերը", "All brands"],
    "Товары бренда": ["Ապրանքանիշի ապրանքները", "Brand products"],
    "Главная": ["Գլխավոր", "Home"],
    "Магазины": ["Խանութներ", "Stores"],
    "Скидки и промокоды": ["Զեղչեր և պրոմոկոդեր", "Discounts and promo codes"],
    "Бренд:": ["Ապրանքանիշ՝", "Brand:"],
    "Подтверждение заявки": ["Հայտի հաստատում", "Request confirmation"],
    "Проверить статус заявки": ["Ստուգել հայտի կարգավիճակը", "Check request status"],
    "Статус заявки": ["Հայտի կարգավիճակ", "Request status"],
    "Менеджер свяжется с вами, чтобы подтвердить наличие, итоговую сумму и способ получения.": [
      "Մենեջերը կկապվի ձեզ հետ՝ հաստատելու առկայությունը, վերջնական գումարը և ստացման եղանակը։",
      "Your manager will contact you to confirm availability, the total and delivery or collection."
    ],
    "Сохранить ссылку на статус заявки": ["Պահպանել հայտի կարգավիճակի հղումը", "Save the request tracking link"],
    "Убрать из избранного": ["Հեռացնել նախընտրածներից", "Remove from wishlist"],
    "В корзину": ["Ավելացնել զամբյուղ", "Add to bag"],
    "В избранном пока нет товаров.": ["Նախընտրածների ցանկը դեռ դատարկ է։", "Your wishlist is empty."],
    "Сохраняйте светильники, к которым хотите вернуться.": ["Պահպանեք այն լուսատուները, որոնց ցանկանում եք վերադառնալ։", "Save the lights you want to revisit."],
    "Товар добавлен в избранное.": ["Ապրանքն ավելացվել է նախընտրածներում։", "Added to your wishlist."],
    "Товар удалён из избранного.": ["Ապրանքը հեռացվել է նախընտրածներից։", "Removed from your wishlist."],
    "Товар сейчас недоступен.": ["Ապրանքն այժմ հասանելի չէ։", "This product is currently unavailable."],
    "Откройте приватную ссылку, выданную после оформления заявки.": ["Բացեք հայտը ուղարկելուց հետո ստացած անձնական հղումը։", "Open the private tracking link you received after placing your request."],
    "Проверяем статус заявки…": ["Ստուգում ենք հայտի կարգավիճակը…", "Checking your request status…"],
    "Заявка не найдена. Проверьте приватную ссылку.": ["Հայտը չի գտնվել։ Ստուգեք անձնական հղումը։", "Request not found. Check your private tracking link."],
    "Статус временно недоступен. Попробуйте позже.": ["Կարգավիճակը ժամանակավորապես անհասանելի է։ Փորձեք ավելի ուշ։", "Status is temporarily unavailable. Try again later."],
    "Не удалось проверить статус. Попробуйте обновить страницу.": ["Չհաջողվեց ստուգել կարգավիճակը։ Թարմացրեք էջը։", "Could not check the status. Try refreshing the page."],
    "Сейчас статистика разрешена.": ["Վիճակագրության հավաքումը թույլատրված է։", "Analytics are currently allowed."],
    "Сейчас выбраны только необходимые настройки.": ["Ընտրված են միայն անհրաժեշտ կարգավորումները։", "Only essential settings are enabled."],
    "Выбор действует на этой странице. Браузер не сохранил настройки.": [
      "Ընտրությունը գործում է այս էջում։ Դիտարկիչը չի պահպանել կարգավորումները։",
      "Your choice applies to this page. The browser could not save your preferences."
    ],
    "Высота": ["Բարձրություն", "Height"],
    "Глубина": ["Խորություն", "Depth"],
    "Длина подвеса": ["Կախոցի երկարություն", "Suspension length"],
    "Защита IP": ["IP պաշտպանություն", "IP rating"],
    "Индекс цветопередачи CRI / Ra": ["Գունարտադրման ինդեքս CRI / Ra", "Color rendering index CRI / Ra"],
    "Источник света": ["Լույսի աղբյուր", "Light source"],
    "Количество ламп": ["Լամպերի քանակ", "Number of lamps"],
    "Материал": ["Նյութ", "Material"],
    "Мощность": ["Հզորություն", "Power"],
    "Напряжение питания": ["Սնուցման լարում", "Supply voltage"],
    "Регулируемый подвес": ["Կարգավորվող կախոց", "Adjustable suspension"],
    "Световой поток": ["Լուսային հոսք", "Luminous flux"],
    "Угол рассеивания": ["Լույսի տարածման անկյուն", "Beam angle"],
    "Цвет корпуса": ["Կորպուսի գույն", "Finish"],
    "Цвет свечения": ["Լույսի գույն", "Light color"],
    "Цветовая температура": ["Գունային ջերմաստիճան", "Color temperature"],
    "Цоколь": ["Լամպակոթ", "Lamp base"],
    "Ширина": ["Լայնություն", "Width"]
  };
  const labels = {ru: "RU", hy: "Հայ", en: "EN"};
  let language = "ru";
  try {
    const saved = localStorage.getItem("lusar-language");
    if (Object.hasOwn(labels, saved)) language = saved;
  } catch {}

  function text(source) {
    const trimmed = source.trim();
    const arrow = trimmed.match(/^(.*?)\s*([→↗])$/u);
    const base = arrow ? arrow[1] : trimmed;
    let translated = language === "ru" ? base : translations[base]?.[language === "hy" ? 0 : 1];
    if (translated === undefined) {
      const count = trimmed.match(/^Товаров: (\d+)$/u);
      if (count) translated = language === "hy" ? "Ապրանքներ՝ " + count[1] : language === "en" ? "Products: " + count[1] : trimmed;
    }
    if (translated === undefined && language !== "ru") {
      const photo = trimmed.match(/^Фото (\d+)$/u);
      if (photo) translated = (language === "hy" ? "Լուսանկար " : "Photo ") + photo[1];
      const sku = trimmed.match(/^Артикул (.+)$/u);
      const receipt = trimmed.match(/^Заявка №(LS-(?:[0-9]{6}|[A-F0-9]{12})) получена\.$/u);
      const tracking = trimmed.match(/^Заявка №(LS-(?:[0-9]{6}|[A-F0-9]{12})): (.+)\.$/u);
      const quantity = trimmed.match(/^Товар в корзине\. Количество: (\d+)\.$/u);
      const hours = trimmed.match(/^Часы связи с менеджером: (.+)\.$/u);
      if (sku) translated = (language === "hy" ? "Արտիկուլ " : "SKU ") + sku[1];
      if (receipt) translated = language === "hy" ? "Հայտը №" + receipt[1] + " ստացվել է։" : "Request #" + receipt[1] + " received.";
      if (tracking) translated = (language === "hy" ? "Հայտ №" : "Request #") + tracking[1] + ": " + text(tracking[2]);
      if (quantity) translated = language === "hy" ? "Ավելացվել է զամբյուղում։ Քանակ՝ " + quantity[1] + "։" : "Added to bag. Quantity: " + quantity[1] + ".";
      if (hours) translated = (language === "hy" ? "Կապի ժամերը՝ " : "Contact hours: ") + hours[1] + ".";
    }
    if (translated === undefined) return source;
    const result = translated + (arrow ? " " + arrow[2] : "");
    return source.replace(trimmed, result);
  }

  const nodes = new WeakMap();
  const attributes = new WeakMap();
  const excluded = "script, style, noscript, textarea, .language-control, [data-locale-source]";

  function translateNode(node) {
    if (!node.parentElement || node.parentElement.closest(excluded)) return;
    const previous = nodes.get(node);
    const source = previous?.rendered === node.data ? previous.source : node.data;
    const rendered = text(source);
    nodes.set(node, {source, rendered});
    if (node.data !== rendered) node.data = rendered;
  }

  function translateElement(element) {
    if (element.closest(excluded)) return;
    let original = attributes.get(element);
    if (!original) {
      original = {};
      for (const name of ["aria-label", "title", "placeholder"]) {
        if (element.hasAttribute(name)) original[name] = element.getAttribute(name);
      }
      attributes.set(element, original);
    }
    for (const [name, source] of Object.entries(original)) element.setAttribute(name, text(source));
  }

  function translateTree(root) {
    if (root.nodeType === Node.TEXT_NODE) {
      translateNode(root);
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE) return;
    translateElement(root);
    for (const element of root.querySelectorAll("[aria-label], [title], [placeholder]")) translateElement(element);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) translateNode(walker.currentNode);
  }

  const originalTitle = document.title;
  const picker = document.querySelector("#language");
  function apply() {
    document.documentElement.lang = language;
    picker.value = language;
    document.querySelector("#language-display").textContent = labels[language];
    translateTree(document.body);
    document.title = text(originalTitle.replace(/ — LUSAR$/u, "")) + " — LUSAR";
    document.dispatchEvent(new Event("lusar-language-change"));
  }

  window.lusarLocale = {text};
  picker.addEventListener("change", () => {
    language = picker.value;
    try { localStorage.setItem("lusar-language", language); } catch {}
    apply();
  });
  apply();
  picker.parentElement.hidden = false;
  new MutationObserver(changes => {
    for (const change of changes) {
      if (change.type === "characterData") translateNode(change.target);
      else for (const node of change.addedNodes) translateTree(node);
    }
  }).observe(document.body, {subtree: true, childList: true, characterData: true});
})();
