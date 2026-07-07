# Nova Assistant

Voice assistant project inspired by the classic Google Assistant experience.

> Status: the project is currently undergoing a major architecture rebuild, so some functionality may be unstable or temporarily unavailable.

---

## 🇬🇧 English

Nova Assistant is a voice assistant for **Linux** and **Windows**.

### Planned improvements
- [ ] Flexible plugin system for user-made commands
- [ ] Better cross-platform support
- [ ] Useful built-in commands out of the box
- [ ] Assistant overlay similar to Google Assistant

---

## 🇷🇺 Русский

Nova Assistant — это голосовой помощник для **Linux** и **Windows**, вдохновлённый классическим Google Assistant.

### Текущий статус
Проект находится на этапе глобальной перестройки архитектуры, поэтому часть функций может быть временно недоступна.

### Планы
- [ ] Гибкая система пользовательских плагинов
- [ ] Улучшенная мультиплатформенная поддержка
- [ ] Полезные встроенные команды «из коробки»
- [ ] Оверлей в стиле Google Assistant

---

## 🇺🇦 Українська

Nova Assistant — це голосовий помічник для **Linux** і **Windows**, натхненний класичним Google Assistant.

### Поточний статус
Проєкт перебуває на етапі глобальної перебудови архітектури, тому частина функцій може бути тимчасово недоступна.

### Плани
- [ ] Гнучка система користувацьких плагінів
- [ ] Покращена багатоплатформна підтримка
- [ ] Корисні вбудовані команди «з коробки»
- [ ] Оверлей у стилі Google Assistant

---

## Quick start

```bash
pip install -r requirements.txt
python main.py
```

Available run arguments:

- `--mlmodel` — path to intent model file
- `--sttmodel` — path to STT model directory
- `--ttsmodel` — path to TTS model directory

---

## Plugin system

Plugin development guides are available in:

- `/home/runner/work/nova-assistant/nova-assistant/PluginSystem/dev.md` (English)
- `/home/runner/work/nova-assistant/nova-assistant/PluginSystem/devRU.md` (Русский)
- `/home/runner/work/nova-assistant/nova-assistant/PluginSystem/devUA.md` (Українська)