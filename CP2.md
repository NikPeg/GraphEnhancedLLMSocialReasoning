CP2- "Мафия с LLM и графовым анализом"

## Ключевая идея проекта
Исследуем влияние графовых представлений на способности языковых моделей в социальной дедуктивной игре "Мафия". Модифицируем существующий проект, добавляя различные типы графов для улучшения контекстного понимания и стратегического мышления LLM-агентов.
Для тестирования актуальной функциональности можно воспользоваться телеграм-ботом https://t.me/llmmafiabot

## Подход к построению и использованию графов
Для построения всех четырех типов графов (коммуникационный, профиль игрока, текущего раунда, глобальный) мы будем использовать отдельную аналитическую LLM, которая будет:

1. Анализировать сообщения и действия игроков
2. Выявлять отношения, поведенческие паттерны и стратегии
3. Формировать структурированные графы с помощью NetworkX
4. Генерировать текстовые описания графов для инжекции в контекст игроков

**Преимущества этого подхода:**
- Избегаем жестких эвристик и правил
- Получаем гибкий анализ естественного языка
- Выявляем сложные социальные паттерны
- Создаем понятные для LLM текстовые представления графов

## План экспериментов

1. **Базовый эксперимент**: 6 идентичных LLM-агентов играют без графовой информации
2. **Эксперимент с глобальной историей**: Инжекция глобального графа игры
3. **Эксперимент с текущим контекстом**: Инжекция графа текущего раунда
4. **Комбинированный эксперимент**: Одновременная инжекция нескольких типов графов

## Текущее состояние проекта
Мы находимся на этапе разработки архитектуры построения графов. Используем модифицированный фреймворк llm-mafia-game, где:

1. Ядро игровой логики останется без изменений
2. Добавим систему анализа взаимодействий с помощью отдельной LLM
3. Разработаем механизм построения четырех типов графов:
   - **Коммуникационный граф**: Игроки как узлы, высказывания как направленные ребра с атрибутами тона, типа взаимодействия и уверенности
   - **Граф профиля игрока**: Центральный узел игрока, связанный с узлами поведенческих паттернов и характеристик
   - **Граф текущего раунда**: Фокус на взаимодействиях только в рамках текущего дня/ночи
   - **Глобальный граф**: Агрегация всей игровой истории с хронологией событий

## Исследовательский набор данных
Данные генерируются в процессе игровых сессий:
- Логи диалогов между LLM-агентами
- Записи голосований и их результаты
- Исходы игр (победы/поражения)
- Графовые представления всех взаимодействий

## Дизайн сети
- **Узлы**: Игроки и их характеристики
- **Ребра**: Различные типы взаимодействий (обвинения, защита, вопросы, голосования)
- **Атрибуты ребер**: Тип взаимодействия, эмоциональная окраска, уверенность, хронология

Планируем анализировать:
- Центральность игроков в коммуникационном графе
- Плотность связей между игроками
- Последовательность/противоречивость в действиях игроков

В нашем проекте используются четыре взаимодополняющих типа графов, каждый из которых представляет игру "Мафия" с разных перспектив:
## 1. Коммуникационный граф
**Структура:**
- **Узлы:** Игроки (LLM-агенты)
- **Рёбра:** Направленные связи коммуникации между игроками
- **Атрибуты рёбер:** Тип взаимодействия (обвинение, защита, вопрос), эмоциональная окраска, уверенность говорящего, частота

**Пример:**
```
Игрок1 ----[обвинение, негативный тон, высокая уверенность]---> Игрок3
Игрок2 ----[защита, позитивный тон, средняя уверенность]-----> Игрок3
Игрок4 ----[вопрос, нейтральный тон, низкая уверенность]----> Игрок1
```
В реальной игре: Игрок1 агрессивно обвиняет Игрока3 в принадлежности к мафии ("Я уверен, что Игрок3 - мафия!"), в то время как Игрок2 пытается защитить Игрока3 ("Мне кажется, Игрок3 ведёт себя как мирный житель").

## 2. Граф профиля игрока в сессии
**Структура:**
- **Центральный узел:** Конкретный игрок
- **Связанные узлы:** Поведенческие паттерны и характеристики
- **Атрибуты связей:** Степень уверенности, раунд первого наблюдения, частота проявления

**Пример:**


```
              	     [агрессивное обвинение]
                           ↑
                          0.8
                           ↑
[защита других]< ----0.6---- Игрок2----0.4----> [изменение позиции]
                           ↓
                          0.3
                           ↓
                   [логические противоречия]
```
В реальной игре: Анализ показывает, что Игрок2 часто защищает других (уверенность 0.6), иногда агрессивно обвиняет (0.8), редко меняет свою позицию (0.4) и в его высказываниях изредка встречаются противоречия (0.3).

## 3. Граф текущего раунда

**Структура:**
- **Узлы:** Активные игроки в данном раунде
- **Рёбра:** Взаимодействия только текущего раунда
- **Атрибуты узлов:** Активность (количество сообщений)
- **Атрибуты рёбер:** Тип взаимодействия, результаты голосования

**Пример для Дня 2:**
```
Игрок1(5) ----[обвинение]----> Игрок3(3)
    ↓              ↑
[голос]            |
    ↓       [голос]|
Игрок5(1) <---[обвинение]---- Игрок4(4)
    ↑
[голос]
    |
Игрок2(2)
```

В реальной игре: В День 2 Игрок1 (самый активный с 5 сообщениями) обвиняет Игрока3, Игрок4 обвиняет Игрока5. При голосовании Игрок1 и Игрок4 голосуют против Игрока3, а Игрок2 и Игрок3 голосуют против Игрока5.

## 4. Глобальный граф игры

**Структура:**
- **Узлы:** Все игроки (включая выбывших) и ключевые события
- **Рёбра:** Агрегированные взаимодействия за всю игру
- **Атрибуты узлов:** Статус (жив/мертв), роль (если раскрыта), активность по раундам
- **Атрибуты рёбер:** Хронология взаимодействий, накопленные типы отношений

**Пример для игры после 3 раундов:**
```
Игрок1(жив) ----[8 взаимодействий, преим. обвинения]----> Игрок3(мертв,Р2)
    |                                                        ↑
    |                                                        |
[5 взаимодействий]                         [6 взаимодействий, защита]
    |                                                        |
    ↓                                                        |
Игрок5(жив) <-----[3 взаимодействия, вопросы]--------- Игрок2(жив)
    ↑
[голосование Р3]
    |
Игрок4(жив)
```
В реальной игре: Глобальный граф показывает, что Игрок1 часто взаимодействовал с Игроком3 (8 раз, преимущественно обвинения) до его исключения во втором раунде. Игрок2 последовательно защищал Игрока3. В третьем раунде Игрок4 проголосовал против Игрока5.

Все эти графы создаются и обновляются аналитической LLM, которая анализирует сообщения игроков и действия в игре, затем формирует структурированные графовые представления и генерирует их текстовые описания для инжекции в контекст игроков.

Наш ключевой вклад - использование отдельной аналитической LLM для построения всех типов графов вместо жестких правил, что позволит выявлять сложные социальные паттерны и создавать информативные контексты для игровых агентов.# Network Design and Framing
