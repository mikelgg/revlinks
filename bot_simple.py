# type: ignore
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import re
import logging
import sys

# Configuración de logging mínima
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)

# Desactivar logs de las bibliotecas
logging.getLogger('httpx').setLevel(logging.CRITICAL)
logging.getLogger('httpcore').setLevel(logging.CRITICAL)
logging.getLogger('telegram').setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

# CONFIGURACIÓN DEL BOT
TOKEN = "8216383033:AAFXh-ci1Y0iNJ1_4fEkc0lZKk4lhY96Azg"
OOTDBUY_INVITE = "9T2IQQ3H1"
WEMIMI_ID = "2513637169127302844"

# Estados globales para cada chat
chat_states = {}
chat_data = {}

def generate_links(product_url, item_id):
    """Genera todos los enlaces necesarios"""
    encoded_url = requests.utils.quote(product_url)
    double_encoded_url = requests.utils.quote(encoded_url)

    if "weidian.com" in product_url:
        channel = "weidian"
        finderqc_url = f"https://finderqc.com/product/Weidian/{item_id}"
        kakubuy_url = f"https://www.kakobuy.com/item/details?url={encoded_url}"
    elif "taobao.com" in product_url:
        channel = "TAOBAO"
        finderqc_url = f"https://finderqc.com/product/Taobao/{item_id}"
        kakubuy_url = f"https://www.kakobuy.com/item/details?url={encoded_url}"
    else:  # 1688.com
        channel = "1688"
        finderqc_url = f"https://finderqc.com/product/Ali1688/{item_id}"
        # KAKUBUY para 1688 - convertir a formato móvil
        mobile_1688_url = product_url.replace("detail.1688.com/offer/", "m.1688.com/offer/").replace(".html", ".html?ptow=113d26e7c9a")
        kakubuy_url = f"https://www.kakobuy.com/item/details?url={requests.utils.quote(mobile_1688_url)}"

    links = {
        'ootdbuy': f"https://www.ootdbuy.com/goods/details?id={item_id}&channel={channel}&inviteCode={OOTDBUY_INVITE}",
        'wemimi': f"https://www.wemimi.com/#/home/productDetail?productLink={double_encoded_url}&memberId={WEMIMI_ID}",
        'kakubuy': kakubuy_url,
        'finderqc': finderqc_url
    }

    return links

def extract_item_id(url):
    """Extraer el ID del producto de diferentes plataformas"""
    if "1688.com" in url:
        pattern = r'offer/(\d+)\.html'
    elif "weidian.com" in url:
        pattern = r'itemID=(\d+)'
    elif "taobao.com" in url:
        pattern = r'id=(\d+)'
    else:
        return None

    match = re.search(pattern, url)
    return match.group(1) if match else None

async def iniciar_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /iniciar para grupos"""
    message = update.message
    chat_id = message.chat_id
    thread_id = message.message_thread_id
    
    # Crear clave única para chat+thread
    chat_key = f"{chat_id}_{thread_id}" if thread_id else str(chat_id)
    
    print(f"🚀 /iniciar en chat_key: {chat_key}")
    
    # Inicializar estado
    chat_states[chat_key] = "ESPERANDO_TITULO"
    chat_data[chat_key] = {
        "mensajes_a_eliminar": [message.message_id],
        "thread_id": thread_id
    }
    
    # Enviar mensaje
    response = await context.bot.send_message(
        chat_id=chat_id,
        text="Por favor, envía el título del producto:",
        message_thread_id=thread_id
    )
    
    chat_data[chat_key]["mensajes_a_eliminar"].append(response.message_id)
    print(f"✅ Estado inicializado: {chat_states[chat_key]}")

async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa todos los mensajes en grupos"""
    message = update.message
    if not message:
        return
        
    chat_id = message.chat_id
    thread_id = message.message_thread_id
    chat_key = f"{chat_id}_{thread_id}" if thread_id else str(chat_id)
    
    print(f"📨 Mensaje recibido en chat_key: {chat_key}")
    
    # Verificar si hay un estado activo
    if chat_key not in chat_states:
        print(f"❌ No hay estado activo para {chat_key}")
        return
    
    estado = chat_states[chat_key]
    print(f"📋 Estado actual: {estado}")
    
    # Agregar mensaje a la lista de eliminación
    chat_data[chat_key]["mensajes_a_eliminar"].append(message.message_id)
    
    try:
        if estado == "ESPERANDO_TITULO":
            await manejar_titulo(update, context, chat_key)
        elif estado == "ESPERANDO_IMAGEN":
            await manejar_imagen(update, context, chat_key)
        elif estado == "ESPERANDO_ENLACE":
            await manejar_enlace(update, context, chat_key)
    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}")
        await message.reply_text(f"Error: {str(e)}")

async def manejar_titulo(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_key: str):
    """Maneja el título del producto"""
    message = update.message
    
    if message.text:
        titulo = message.text.strip()
        chat_data[chat_key]["titulo"] = titulo
        chat_states[chat_key] = "ESPERANDO_IMAGEN"
        
        response = await context.bot.send_message(
            chat_id=message.chat_id,
            text="Título guardado. Ahora envía la imagen o escribe 'saltar':",
            message_thread_id=chat_data[chat_key]["thread_id"]
        )
        
        chat_data[chat_key]["mensajes_a_eliminar"].append(response.message_id)
        print(f"✅ Título guardado: {titulo}")

async def manejar_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_key: str):
    """Maneja la imagen del producto"""
    message = update.message
    
    if message.photo:
        # Imagen enviada directamente
        photo_id = message.photo[-1].file_id
        chat_data[chat_key]["imagen"] = photo_id
        chat_data[chat_key]["es_file_id"] = True
        print(f"✅ Imagen (file_id) guardada")
    elif message.text:
        text = message.text.strip().lower()
        if text in ["saltar", "skip", "no", "ninguna"]:
            chat_data[chat_key]["imagen"] = ""
            print(f"✅ Imagen saltada")
        else:
            # Asumir que es una URL de imagen
            chat_data[chat_key]["imagen"] = message.text.strip()
            print(f"✅ Imagen (URL) guardada")
    
    # Cambiar estado
    chat_states[chat_key] = "ESPERANDO_ENLACE"
    
    response = await context.bot.send_message(
        chat_id=message.chat_id,
        text="Imagen guardada. Ahora envía el enlace del producto:",
        message_thread_id=chat_data[chat_key]["thread_id"]
    )
    
    chat_data[chat_key]["mensajes_a_eliminar"].append(response.message_id)

async def manejar_enlace(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_key: str):
    """Maneja el enlace del producto y genera el resultado final"""
    message = update.message
    
    if not message.text:
        return
    
    product_url = message.text.strip()
    datos = chat_data[chat_key]
    titulo = datos.get("titulo", "")
    imagen = datos.get("imagen", "")
    
    try:
        # Procesar enlace de Sugargoo si es necesario
        if "sugargoo.com" in product_url:
            product_link_match = re.search(r'productLink=(.*?)(?:&|$)', product_url)
            if product_link_match:
                product_url = requests.utils.unquote(product_link_match.group(1))
        
        # Extraer ID del producto
        item_id = extract_item_id(product_url)
        if not item_id:
            await message.reply_text("❌ No se pudo extraer el ID del producto. Verifica el enlace.")
            return
        
        # Generar enlaces
        links = generate_links(product_url, item_id)
        
        # Crear mensaje final
        message_text = f"{titulo}🔥\n\n"
        message_text += f"<a href='{links['ootdbuy']}'>OOTDBUY</a>/<a href='{links['kakubuy']}'>KAKOBUY</a>/<a href='{links['wemimi']}'>WEMIMI</a>\n\n"
        message_text += f"QC:\n"
        message_text += f"<a href='{links['finderqc']}'>FINDERQC</a>"
        
        # Eliminar mensajes intermedios
        for msg_id in datos["mensajes_a_eliminar"]:
            try:
                await context.bot.delete_message(chat_id=message.chat_id, message_id=msg_id)
            except:
                pass
        
        # Enviar resultado final
        if imagen:
            try:
                await context.bot.send_photo(
                    chat_id=message.chat_id,
                    photo=imagen,
                    caption=message_text,
                    parse_mode='HTML',
                    message_thread_id=datos["thread_id"]
                )
            except Exception as e:
                print(f"Error enviando imagen: {e}")
                await context.bot.send_message(
                    chat_id=message.chat_id,
                    text=message_text,
                    parse_mode='HTML',
                    message_thread_id=datos["thread_id"]
                )
        else:
            await context.bot.send_message(
                chat_id=message.chat_id,
                text=message_text,
                parse_mode='HTML',
                message_thread_id=datos["thread_id"]
            )
        
        print(f"✅ Proceso completado para {chat_key}")
        
    except Exception as e:
        print(f"❌ Error procesando enlace: {e}")
        await message.reply_text(f"❌ Error procesando enlace: {str(e)}")
    
    # Limpiar estado
    if chat_key in chat_states:
        del chat_states[chat_key]
    if chat_key in chat_data:
        del chat_data[chat_key]

async def cancelar_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /cancelar"""
    message = update.message
    chat_id = message.chat_id
    thread_id = message.message_thread_id
    chat_key = f"{chat_id}_{thread_id}" if thread_id else str(chat_id)
    
    if chat_key in chat_states:
        # Eliminar mensajes intermedios
        if chat_key in chat_data:
            for msg_id in chat_data[chat_key]["mensajes_a_eliminar"]:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except:
                    pass
        
        # Limpiar estado
        del chat_states[chat_key]
        if chat_key in chat_data:
            del chat_data[chat_key]
        
        await message.reply_text("❌ Proceso cancelado. Usa /iniciar para empezar de nuevo.")
    else:
        await message.reply_text("No hay ningún proceso activo para cancelar.")

def main():
    try:
        application = Application.builder().token(TOKEN).build()
        
        print("🤖 Iniciando bot simplificado...")
        
        # Comandos
        application.add_handler(CommandHandler("iniciar", iniciar_comando))
        application.add_handler(CommandHandler("cancelar", cancelar_comando))
        
        # Mensajes en grupos (solo grupos, no privados)
        application.add_handler(MessageHandler(
            (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP) & ~filters.COMMAND,
            procesar_mensaje
        ))
        
        print("✅ Bot iniciado correctamente")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error crítico del bot: {e}")
        print(f"❌ Error crítico: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
