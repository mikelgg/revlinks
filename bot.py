# type: ignore
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import requests
from bs4 import BeautifulSoup
import re
import os
import logging
import sys

# Modificar la configuración de logging para que sea mínima
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)

# Desactivar logs de las bibliotecas
logging.getLogger('httpx').setLevel(logging.CRITICAL)
logging.getLogger('httpcore').setLevel(logging.CRITICAL)
logging.getLogger('telegram').setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

# Tokens y códigos
TOKEN = "8216383033:AAFXh-ci1Y0iNJ1_4fEkc0lZKk4lhY96Azg"
OOTDBUY_INVITE = "9T2IQQ3H1"
WEMIMI_ID = "2513637169127302844"

# Estados para la conversación
TITULO, IMAGEN, ENLACE = range(3)
datos_temporales = {}
canal_estado = {}
canal_datos = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Vamos a crear tu enlace paso a paso.\n"
        "Por favor, envíame primero el título del producto:"
    )
    return TITULO

async def recibir_titulo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    datos_temporales[user_id] = {'titulo': update.message.text}
    await update.message.reply_text("Título guardado. Ahora envía la imagen o el enlace de la imagen: (o escribe 'cancelar' para detener el proceso)")
    return IMAGEN

async def recibir_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message = update.message
    
    # Verificar si es una foto enviada directamente
    if message.photo:
        # Usar el ID de la foto más grande (mejor calidad)
        photo_id = message.photo[-1].file_id
        datos_temporales[user_id]['imagen'] = photo_id
        datos_temporales[user_id]['es_file_id'] = True  # Marcar que es un file_id
        await message.reply_text("Imagen guardada. Por último, envíame el enlace de Sugargoo o el enlace directo de 1688/Weidian/Taobao:")
        return ENLACE
    
    # Si es texto (URL de imagen)
    elif message.text:
        text = message.text.strip()
        
        # Verificar si quiere saltar la imagen
        if text.lower() in ["saltar", "skip", "no", "ninguna"]:
            datos_temporales[user_id]['imagen'] = ""
            await message.reply_text("Imagen omitida. Por último, envíame el enlace de Sugargoo o el enlace directo de 1688/Weidian/Taobao:")
            return ENLACE
        
        # Si es una URL de imagen
        else:
            datos_temporales[user_id]['imagen'] = text
            await message.reply_text("Imagen guardada. Por último, envíame el enlace de Sugargoo o el enlace directo de 1688/Weidian/Taobao:")
            return ENLACE
    
    # Si no es ni foto ni texto válido
    else:
        await message.reply_text("Por favor envía una imagen, una URL de imagen, o escribe 'saltar' para omitir este paso.")
        return IMAGEN

async def recibir_enlace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message = update.message
    product_url = message.text
    
    datos = datos_temporales.get(user_id, {})
    title = datos.get('titulo', '')
    image_url = datos.get('imagen', '')
    
    try:
        # Si es un enlace de Sugargoo, extraer el enlace original
        if "sugargoo.com" in product_url:
            product_link_match = re.search(r'productLink=(.*?)(?:&|$)', product_url)
            if not product_link_match:
                raise ValueError("No se pudo encontrar el enlace del producto")
            product_url = requests.utils.unquote(product_link_match.group(1))
        
        # Obtener el ID del producto
        item_id = extract_item_id(product_url)
        if not item_id:
            raise ValueError("No se pudo extraer el ID del producto")
        
        # Generar todos los enlaces
        links = generate_links(product_url, item_id)
        
        # Preparar el mensaje con los enlaces integrados
        message_text = f"{title}🔥\n\n"
        message_text += f"<a href='{links['ootdbuy']}'>OOTDBUY</a>/<a href='{links['kakubuy']}'>KAKOBUY</a>/<a href='{links['wemimi']}'>WEMIMI</a>\n\n"
        message_text += f"QC:\n"
        message_text += f"<a href='{links['finderqc']}'>FINDERQC</a>"

        # Enviar al usuario
        if image_url:
            try:
                # Verificar si es un file_id o una URL
                if datos.get('es_file_id', False):
                    # Si es un file_id, usar directamente
                    await message.reply_photo(
                        photo=image_url,
                        caption=message_text,
                        parse_mode='HTML'
                    )
                else:
                    # Si es una URL, usar como antes
                    await message.reply_photo(
                        photo=image_url,
                        caption=message_text,
                        parse_mode='HTML'
                    )
            except Exception as e:
                print(f"Error al enviar imagen: {e}")
                await message.reply_text(message_text, parse_mode='HTML')
        else:
            await message.reply_text(message_text, parse_mode='HTML')


    except Exception as e:
        await message.reply_text(f"Error al procesar el enlace: {str(e)}")
        print(f"Error: {e}")
    
    # Limpiar datos temporales
    if user_id in datos_temporales:
        del datos_temporales[user_id]
    
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in datos_temporales:
        del datos_temporales[user_id]
    await update.message.reply_text("Proceso cancelado. Puedes empezar de nuevo con /start")
    return ConversationHandler.END

def generate_links(product_url, item_id):
    """Genera todos los enlaces necesarios"""
    encoded_url = requests.utils.quote(product_url)
    double_encoded_url = requests.utils.quote(encoded_url)

    if "weidian.com" in product_url:
        channel = "weidian"
        finderqc_url = f"https://finderqc.com/product/Weidian/{item_id}"
        # KAKUBUY para Weidian
        kakubuy_url = f"https://www.kakobuy.com/item/details?url={encoded_url}"
    elif "taobao.com" in product_url:
        channel = "TAOBAO"
        finderqc_url = f"https://finderqc.com/product/Taobao/{item_id}"
        # KAKUBUY para Taobao
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

async def process_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if not message:
        return
    
    chat_id = message.chat_id
    
    # Determinar el tipo de contenido
    content_type = "desconocido"
    content_data = None
    
    if message.text:
        content_type = "texto"
        content_data = message.text.strip()
        
        # Verificar si quiere cancelar el proceso (solo para mensajes de texto)
        if content_data.lower() in ["cancelar", "cancel", "stop", "parar", "detener"]:
            if chat_id in canal_estado:
                del canal_estado[chat_id]
            if chat_id in canal_datos:
                del canal_datos[chat_id]
            await context.bot.send_message(
                chat_id=chat_id,
                text="Proceso cancelado. Puedes iniciar uno nuevo escribiendo 'iniciar'."
            )
            return
        
        # Iniciar proceso en el canal (solo para mensajes de texto)
        if content_data.lower() in ["iniciar", "crear", "nuevo", "/iniciar", "/crear", "/nuevo"]:
            # Inicializar estado y datos
            canal_estado[chat_id] = "TITULO"
            canal_datos[chat_id] = {
                "mensajes_a_eliminar": []
            }
            
            # Enviar mensaje de instrucciones
            response = await context.bot.send_message(
                chat_id=chat_id,
                text="🔄 <b>Proceso iniciado</b>\n\nPor favor, envía el título del producto:",
                parse_mode='HTML'
            )
            
            # Guardar ID del mensaje para eliminarlo después
            canal_datos[chat_id]["mensajes_a_eliminar"].append(response.message_id)
            return
    elif message.photo:
        content_type = "foto"
        content_data = message.photo[-1].file_id
        caption = message.caption
        
        # Si hay un caption, procesarlo como texto adicional
        if caption and chat_id in canal_estado:
            if canal_estado[chat_id] == "IMAGEN":
                # Si estamos esperando una imagen, usar esta foto
                canal_datos[chat_id]["imagen"] = content_data
                canal_estado[chat_id] = "ENLACE"
                
                # Enviar mensaje pidiendo el enlace
                response = await context.bot.send_message(
                    chat_id=chat_id,
                    text="✅ Imagen recibida.\n\nAhora envía el enlace del producto:",
                    parse_mode='HTML'
                )
                
                # Guardar ID del mensaje para eliminarlo después
                canal_datos[chat_id]["mensajes_a_eliminar"].append(response.message_id)
                return
    elif message.document:
        content_type = "documento"
        content_data = message.document.file_id
    elif message.video:
        content_type = "video"
        content_data = message.video.file_id
    elif message.audio:
        content_type = "audio"
        content_data = message.audio.file_id
    elif message.voice:
        content_type = "voz"
        content_data = message.voice.file_id
    elif message.sticker:
        content_type = "sticker"
        content_data = message.sticker.file_id
    else:
        # Otro tipo de contenido no manejado específicamente
        return
    
    # Si no hay un estado activo para este canal, ignorar el mensaje
    if chat_id not in canal_estado:
        return
    
    # Procesar según el estado actual
    estado = canal_estado[chat_id]
    
    if estado == "TITULO":
        # Guardar título y pedir imagen
        canal_datos[chat_id]["titulo"] = content_data
        canal_estado[chat_id] = "IMAGEN"
        
        # Enviar mensaje y guardar su ID
        img_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="Título guardado. Ahora envía la imagen o el enlace de la imagen: (o escribe 'cancelar' para detener el proceso)",
            message_thread_id=message.message_thread_id
        )
        canal_datos[chat_id]["mensajes_a_eliminar"].append(img_msg.message_id)
    
    elif estado == "IMAGEN":
        # Si es una foto enviada directamente
        if message.photo:
            # Usar el ID de la foto más grande (mejor calidad)
            photo_id = message.photo[-1].file_id
            canal_datos[chat_id]["imagen"] = photo_id
            canal_datos[chat_id]["es_file_id"] = True  # Marcar que es un file_id y no una URL
            canal_estado[chat_id] = "ENLACE"
            
            # Enviar mensaje y guardar su ID
            enlace_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="Imagen guardada. Por último, envía el enlace de Sugargoo o el enlace directo: (o escribe 'cancelar' para detener el proceso)",
                message_thread_id=message.message_thread_id
            )
            canal_datos[chat_id]["mensajes_a_eliminar"].append(enlace_msg.message_id)
            return

        # Verificar si quiere saltar la imagen
        if content_data.lower() in ["saltar", "skip", "no", "ninguna"]:
            canal_datos[chat_id]["imagen"] = ""
            canal_estado[chat_id] = "ENLACE"
            
            # Enviar mensaje y guardar su ID
            enlace_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="Imagen omitida. Por último, envía el enlace de Sugargoo o el enlace directo: (o escribe 'cancelar' para detener el proceso)",
                message_thread_id=message.message_thread_id
            )
            canal_datos[chat_id]["mensajes_a_eliminar"].append(enlace_msg.message_id)
            
        # Verificar si es una URL de imgur sin http/https
        elif "imgur.com" in content_data or "i.imgur.com" in content_data:
            # Añadir https:// si falta
            if not content_data.startswith("http"):
                image_url = f"https://{content_data}"
            else:
                image_url = content_data
            
            canal_datos[chat_id]["imagen"] = image_url
            canal_estado[chat_id] = "ENLACE"
            
            # Enviar mensaje y guardar su ID
            enlace_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="Imagen guardada. Por último, envía el enlace de Sugargoo o el enlace directo: (o escribe 'cancelar' para detener el proceso)",
                message_thread_id=message.message_thread_id
            )
            canal_datos[chat_id]["mensajes_a_eliminar"].append(enlace_msg.message_id)
            
        # Verificar si es una URL de imagen válida (incluyendo otras plataformas)
        elif (content_data.startswith("http") and 
              (content_data.endswith(".jpg") or content_data.endswith(".jpeg") or content_data.endswith(".png") or 
               content_data.endswith(".webp") or content_data.endswith(".gif") or
               "img" in content_data or "ibb.co" in content_data)):
            # Guardar imagen y pedir enlace
            canal_datos[chat_id]["imagen"] = content_data
            canal_estado[chat_id] = "ENLACE"
            
            # Enviar mensaje y guardar su ID
            enlace_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="Imagen guardada. Por último, envía el enlace de Sugargoo o el enlace directo: (o escribe 'cancelar' para detener el proceso)",
                message_thread_id=message.message_thread_id
            )
            canal_datos[chat_id]["mensajes_a_eliminar"].append(enlace_msg.message_id)
            
        else:
            # Si no parece una URL de imagen, preguntar de nuevo
            error_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="No parece una URL de imagen válida. Puedes enviar una URL de imgur (como i.imgur.com/ejemplo.jpg), escribir 'saltar' para omitir este paso, o 'cancelar' para detener todo el proceso:",
                message_thread_id=message.message_thread_id
            )
            canal_datos[chat_id]["mensajes_a_eliminar"].append(error_msg.message_id)
    
    elif estado == "ENLACE":
        # Procesar el enlace final
        try:
            product_url = content_data
            datos = canal_datos.get(chat_id, {})
            title = datos.get("titulo", "")
            image_url = datos.get("imagen", "")
            
            print(f"Procesando: Título: {title}, Imagen: {image_url}, URL: {product_url}")
            
            # Si es un enlace de Sugargoo, extraer el enlace original
            if "sugargoo.com" in product_url:
                product_link_match = re.search(r'productLink=(.*?)(?:&|$)', product_url)
                if product_link_match:
                    product_url = requests.utils.unquote(product_link_match.group(1))
            
            # Obtener ID y generar enlaces
            item_id = extract_item_id(product_url)
            if not item_id:
                error_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text="No se pudo extraer el ID del producto. Intenta con otro enlace.",
                    message_thread_id=message.message_thread_id
                )
                canal_datos[chat_id]["mensajes_a_eliminar"].append(error_msg.message_id)
                return
            
            links = generate_links(product_url, item_id)
            
            # Crear mensaje final
            message_text = f"{title}🔥\n\n"
            message_text += f"<a href='{links['ootdbuy']}'>OOTDBUY</a>/<a href='{links['kakubuy']}'>KAKOBUY</a>/<a href='{links['wemimi']}'>WEMIMI</a>\n\n"
            message_text += f"QC:\n"
            message_text += f"<a href='{links['finderqc']}'>FINDERQC</a>"
            
            # Eliminar todos los mensajes intermedios
            for msg_id in canal_datos[chat_id].get("mensajes_a_eliminar", []):
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception as e:
                    print(f"Error al eliminar mensaje {msg_id}: {e}")
            
            # Enviar respuesta final
            if image_url:
                try:
                    if canal_datos[chat_id].get("es_file_id", False):
                        # Si es un file_id, usar send_photo directamente con el ID
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=image_url,  # aquí image_url es en realidad el file_id
                            caption=message_text,
                            parse_mode='HTML',
                            message_thread_id=message.message_thread_id
                        )
                    else:
                        # Si es una URL, usar el código existente
                        if "imgur.com" in image_url and not image_url.startswith("https://i."):
                            image_id = image_url.split("/")[-1]
                            image_url = f"https://i.imgur.com/{image_id}.jpg"
                        
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=image_url,
                            caption=message_text,
                            parse_mode='HTML',
                            message_thread_id=message.message_thread_id
                        )
                except Exception as e:
                    print(f"Error al enviar imagen: {e}")
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message_text,
                        parse_mode='HTML',
                        message_thread_id=message.message_thread_id
                    )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode='HTML',
                    message_thread_id=message.message_thread_id
                )
            
            
        except Exception as e:
            print(f"Error en proceso de enlace: {e}")
            error_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"Error al procesar el enlace: {str(e)}",
                message_thread_id=message.message_thread_id
            )
            # No eliminamos este mensaje de error
        
        # Limpiar estado y datos
        if chat_id in canal_estado:
            del canal_estado[chat_id]
        if chat_id in canal_datos:
            del canal_datos[chat_id]

async def process_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return
    
    chat_id = message.chat_id
    message_id = message.message_id
    thread_id = message.message_thread_id  # ID del hilo de discusión si existe
    
    # Determinar el tipo de contenido
    content_type = "desconocido"
    content_data = None
    
    if message.text:
        content_type = "texto"
        content_data = message.text.strip()
    elif message.photo:
        content_type = "foto"
        content_data = message.photo[-1].file_id
    elif message.document:
        content_type = "documento"
        content_data = message.document.file_id
    elif message.video:
        content_type = "video"
        content_data = message.video.file_id
    elif message.audio:
        content_type = "audio"
        content_data = message.audio.file_id
    elif message.voice:
        content_type = "voz"
        content_data = message.voice.file_id
    elif message.sticker:
        content_type = "sticker"
        content_data = message.sticker.file_id
    else:
        # Otro tipo de contenido no manejado específicamente
        return
    
    print(f"Mensaje recibido en grupo: tipo={content_type}")
    print(f"Chat ID: {chat_id}, Thread ID: {thread_id}")
    
    # Crear una clave única para cada chat+hilo
    chat_key = f"{chat_id}_{thread_id}" if thread_id else str(chat_id)
    
    # Si no hay un estado activo para este chat+hilo, ignorar el mensaje
    if chat_key not in canal_estado:
        print(f"No hay estado activo para chat_key: {chat_key}")
        print(f"Estados disponibles: {list(canal_estado.keys())}")
        return
    
    print(f"Procesando mensaje en estado: {canal_estado[chat_key]}")
    
    # Lista para almacenar IDs de mensajes a eliminar después
    if "mensajes_a_eliminar" not in canal_datos[chat_key]:
        canal_datos[chat_key]["mensajes_a_eliminar"] = []
    
    # Guardar ID del mensaje del usuario para eliminarlo después
    canal_datos[chat_key]["mensajes_a_eliminar"].append(message_id)
    
    # Procesar según el estado actual
    estado = canal_estado[chat_key]
    
    if estado == "TITULO":
        # Guardar título y pedir imagen
        canal_datos[chat_key]["titulo"] = content_data
        canal_estado[chat_key] = "IMAGEN"
        
        # Enviar mensaje y guardar su ID
        img_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="Título guardado. Ahora envía la imagen o el enlace de la imagen: (o escribe 'cancelar' para detener el proceso)",
            message_thread_id=thread_id
        )
        canal_datos[chat_key]["mensajes_a_eliminar"].append(img_msg.message_id)
    
    elif estado == "IMAGEN":
        # Si es una foto enviada directamente
        if message.photo:
            # Usar el ID de la foto más grande (mejor calidad)
            photo_id = message.photo[-1].file_id
            canal_datos[chat_key]["imagen"] = photo_id
            canal_datos[chat_key]["es_file_id"] = True  # Marcar que es un file_id y no una URL
            canal_estado[chat_key] = "ENLACE"
            
            # Enviar mensaje y guardar su ID
            enlace_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="Imagen guardada. Por último, envía el enlace de Sugargoo o el enlace directo: (o escribe 'cancelar' para detener el proceso)",
                message_thread_id=thread_id
            )
            canal_datos[chat_key]["mensajes_a_eliminar"].append(enlace_msg.message_id)
            return

        # Verificar si quiere saltar la imagen
        if content_data.lower() in ["saltar", "skip", "no", "ninguna"]:
            canal_datos[chat_key]["imagen"] = ""
            canal_estado[chat_key] = "ENLACE"
            
            # Enviar mensaje y guardar su ID
            enlace_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="Imagen omitida. Por último, envía el enlace de Sugargoo o el enlace directo: (o escribe 'cancelar' para detener el proceso)",
                message_thread_id=thread_id
            )
            canal_datos[chat_key]["mensajes_a_eliminar"].append(enlace_msg.message_id)
            
        # Verificar si es una URL de imgur sin http/https
        elif "imgur.com" in content_data or "i.imgur.com" in content_data:
            # Añadir https:// si falta
            if not content_data.startswith("http"):
                image_url = f"https://{content_data}"
            else:
                image_url = content_data
            
            canal_datos[chat_key]["imagen"] = image_url
            canal_estado[chat_key] = "ENLACE"
            
            # Enviar mensaje y guardar su ID
            enlace_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="Imagen guardada. Por último, envía el enlace de Sugargoo o el enlace directo: (o escribe 'cancelar' para detener el proceso)",
                message_thread_id=thread_id
            )
            canal_datos[chat_key]["mensajes_a_eliminar"].append(enlace_msg.message_id)
            
        # Verificar si es una URL de imagen válida (incluyendo otras plataformas)
        elif (content_data.startswith("http") and 
              (content_data.endswith(".jpg") or content_data.endswith(".jpeg") or content_data.endswith(".png") or 
               content_data.endswith(".webp") or content_data.endswith(".gif") or
               "img" in content_data or "ibb.co" in content_data)):
            # Guardar imagen y pedir enlace
            canal_datos[chat_key]["imagen"] = content_data
            canal_estado[chat_key] = "ENLACE"
            
            # Enviar mensaje y guardar su ID
            enlace_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="Imagen guardada. Por último, envía el enlace de Sugargoo o el enlace directo: (o escribe 'cancelar' para detener el proceso)",
                message_thread_id=thread_id
            )
            canal_datos[chat_key]["mensajes_a_eliminar"].append(enlace_msg.message_id)
            
        else:
            # Si no parece una URL de imagen, preguntar de nuevo
            error_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="No parece una URL de imagen válida. Puedes enviar una URL de imgur (como i.imgur.com/ejemplo.jpg), escribir 'saltar' para omitir este paso, o 'cancelar' para detener todo el proceso:",
                message_thread_id=thread_id
            )
            canal_datos[chat_key]["mensajes_a_eliminar"].append(error_msg.message_id)
    
    elif estado == "ENLACE":
        # Procesar el enlace final
        try:
            product_url = content_data
            datos = canal_datos.get(chat_key, {})
            title = datos.get("titulo", "")
            image_url = datos.get("imagen", "")
            
            print(f"Procesando: Título: {title}, Imagen: {image_url}, URL: {product_url}")
            
            # Si es un enlace de Sugargoo, extraer el enlace original
            if "sugargoo.com" in product_url:
                product_link_match = re.search(r'productLink=(.*?)(?:&|$)', product_url)
                if product_link_match:
                    product_url = requests.utils.unquote(product_link_match.group(1))
            
            # Obtener ID y generar enlaces
            item_id = extract_item_id(product_url)
            if not item_id:
                error_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text="No se pudo extraer el ID del producto. Intenta con otro enlace.",
                    message_thread_id=thread_id
                )
                canal_datos[chat_key]["mensajes_a_eliminar"].append(error_msg.message_id)
                return
            
            links = generate_links(product_url, item_id)
            
            # Crear mensaje final
            message_text = f"{title}🔥\n\n"
            message_text += f"<a href='{links['ootdbuy']}'>OOTDBUY</a>/<a href='{links['kakubuy']}'>KAKOBUY</a>/<a href='{links['wemimi']}'>WEMIMI</a>\n\n"
            message_text += f"QC:\n"
            message_text += f"<a href='{links['finderqc']}'>FINDERQC</a>"
            
            # Eliminar todos los mensajes intermedios
            for msg_id in canal_datos[chat_key].get("mensajes_a_eliminar", []):
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception as e:
                    print(f"Error al eliminar mensaje {msg_id}: {e}")
            
            # Enviar respuesta final
            if image_url:
                try:
                    if canal_datos[chat_key].get("es_file_id", False):
                        # Si es un file_id, usar send_photo directamente con el ID
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=image_url,  # aquí image_url es en realidad el file_id
                            caption=message_text,
                            parse_mode='HTML',
                            message_thread_id=thread_id
                        )
                    else:
                        # Si es una URL, usar el código existente
                        if "imgur.com" in image_url and not image_url.startswith("https://i."):
                            image_id = image_url.split("/")[-1]
                            image_url = f"https://i.imgur.com/{image_id}.jpg"
                        
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=image_url,
                            caption=message_text,
                            parse_mode='HTML',
                            message_thread_id=thread_id
                        )
                except Exception as e:
                    print(f"Error al enviar imagen: {e}")
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message_text,
                        parse_mode='HTML',
                        message_thread_id=thread_id
                    )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode='HTML',
                    message_thread_id=thread_id
                )
            
            
        except Exception as e:
            print(f"Error en proceso de enlace: {e}")
            error_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"Error al procesar el enlace: {str(e)}",
                message_thread_id=thread_id
            )
            # No eliminamos este mensaje de error
        
        # Limpiar estado y datos
        if chat_key in canal_estado:
            del canal_estado[chat_key]
        if chat_key in canal_datos:
            del canal_datos[chat_key]

# Agregar estos manejadores específicos para comandos en grupos
async def iniciar_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador específico para el comando /iniciar en grupos"""
    message = update.message
    if not message:
        return
    
    chat_id = message.chat_id
    message_id = message.message_id
    thread_id = message.message_thread_id
    
    print(f"Comando /iniciar recibido en chat: {chat_id}, thread: {thread_id}")
    
    # Crear una clave única para cada chat+hilo
    chat_key = f"{chat_id}_{thread_id}" if thread_id else str(chat_id)
    
    # Inicializar datos
    canal_estado[chat_key] = "TITULO"
    if chat_key not in canal_datos:
        canal_datos[chat_key] = {"mensajes_a_eliminar": []}
    
    print(f"Estado inicializado para chat_key: {chat_key}")
    print(f"Estado actual: {canal_estado[chat_key]}")
    
    # Guardar ID del mensaje de inicio
    canal_datos[chat_key]["mensajes_a_eliminar"].append(message_id)
    
    # Enviar mensaje pidiendo título
    try:
        titulo_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="Por favor, envía el título del producto:",
            message_thread_id=thread_id
        )
        canal_datos[chat_key]["mensajes_a_eliminar"].append(titulo_msg.message_id)
        print(f"Mensaje de título enviado con ID: {titulo_msg.message_id}")
    except Exception as e:
        print(f"Error al enviar mensaje de título: {e}")

async def cancelar_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador específico para el comando /cancelar en grupos"""
    message = update.message
    if not message:
        return
    
    chat_id = message.chat_id
    thread_id = message.message_thread_id
    
    # Crear una clave única para cada chat+hilo
    chat_key = f"{chat_id}_{thread_id}" if thread_id else str(chat_id)
    
    if chat_key in canal_estado:
        del canal_estado[chat_key]
        
        # Eliminar mensajes intermedios
        for msg_id in canal_datos[chat_key].get("mensajes_a_eliminar", []):
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception as e:
                print(f"Error al eliminar mensaje {msg_id}: {e}")
        
        if chat_key in canal_datos:
            del canal_datos[chat_key]
            
        # Enviar mensaje de cancelación
        await context.bot.send_message(
            chat_id=chat_id,
            text="Proceso cancelado. Puedes iniciar uno nuevo con /iniciar",
            message_thread_id=thread_id
        )


def main():
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Handlers con prioridades correctas
        
        # Comandos específicos para grupos (máxima prioridad)
        application.add_handler(CommandHandler("iniciar", iniciar_comando))
        application.add_handler(CommandHandler("cancelar", cancelar_comando))
        
        # Handlers para mensajes en grupos y canales (alta prioridad)
        application.add_handler(MessageHandler(
            (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP) & ~filters.COMMAND,
            process_group_message
        ))
        
        application.add_handler(MessageHandler(
            filters.ChatType.CHANNEL,
            process_channel_message
        ))
        
        # ConversationHandler para chats privados (baja prioridad)
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                TITULO: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, recibir_titulo)],
                IMAGEN: [MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND & filters.ChatType.PRIVATE, recibir_imagen)],
                ENLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, recibir_enlace)]
            },
            fallbacks=[CommandHandler('cancelar', cancelar)]
        )
        application.add_handler(conv_handler)
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error crítico del bot: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()