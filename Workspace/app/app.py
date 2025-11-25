from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import os
import mercadopago
import traceback
# $env:MERCADOPAGO_ACCESS_TOKEN="APP_USR-5796444415198491-100214-0079dab88cf789d8b4614de5bcc470cd-2901193336"

app = Flask(__name__)
app.secret_key = "tu_clave_secreta"

# Agrega este context processor
@app.context_processor
def inject_auth_button():
    if "usuario" in session:
        return {
            "auth_button_label": "Cerrar sesión",
            "auth_button_url": url_for("logout"),
            "usuario_nombre": session.get("nombre"),
        }
    else:
        return {
            "auth_button_label": "Iniciar sesión",
            "auth_button_url": url_for("login"),
            "usuario_nombre": None,
        }

access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
if not access_token:
    raise Exception(
        "MERCADOPAGO_ACCESS_TOKEN no está definido en las variables de entorno."
    )

sdk = mercadopago.SDK(access_token)


def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost", 
        user="root", 
        password="", 
        database="App_Cobro"
    )
    return conn


@app.route("/")
def main():
    return render_template("main.html")


@app.route("/laptops")
def laptops():
    return render_template("laptops.html")


@app.route("/phones")
def phones():
    return render_template("phones.html")


@app.route("/keyboards")
def keyboards():
    return render_template("keyboards.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM User WHERE email = %s AND password = %s", (email, password)
        )
        user = cursor.fetchone()
        conn.close()
        if user:
            session["usuario"] = user["email"]
            session["nombre"] = user["name"]
            return redirect(url_for("main"))
        else:
            flash("Usuario o contraseña incorrectos")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        dni = request.form["dni"]
        name = request.form["name"]
        last_name = request.form["last_name"]
        birth_day = request.form["birth_day"]
        email = request.form["email"]
        password = request.form["password"]
        credit_card = request.form["credit_card"]
        expiring_date = request.form["expiring_date"]
        cvv = request.form["cvv"]

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO User (dni, name, last_name, birth_day, email, password, credit_card, expiring_date, CVV)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    dni,
                    name,
                    last_name,
                    birth_day,
                    email,
                    password,
                    credit_card,
                    expiring_date,
                    cvv,  # corregido
                ),
            )
            conn.commit()
            flash("Usuario registrado exitosamente", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash("Error al registrar usuario: {}".format(e), "danger")
            return render_template("signup.html")
        finally:
            conn.close()
    return render_template("signup.html")


@app.route("/comprar", methods=["POST"])
def comprar():
    if "usuario" not in session:
        flash("Debes iniciar sesión para comprar.")
        return redirect(url_for("login"))

    producto = request.form["producto"]
    cantidad = int(request.form["cantidad"])

    if producto == "Productos" or not producto:
        flash("Selecciona un producto válido.")
        return redirect(url_for("keyboards"))

    back_urls = {
        "success": "http://localhost:5000/pago_exitoso",
        "failure": "http://localhost:5000/pago_fallido",
        "pending": "http://localhost:5000/pago_pendiente",
    }

    preference_data = {
        "items": [
            {
                "title": producto,
                "quantity": cantidad,
                "currency_id": "ARS",
                "unit_price": 1500.00,
            }
        ],
        "back_urls": back_urls,
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        print("Respuesta completa de Mercado Pago:", preference_response)

        if (
            "response" in preference_response
            and "init_point" in preference_response["response"]
        ):
            init_point = preference_response["response"]["init_point"]
            return redirect(init_point)
        else:
            flash("No se pudo generar el checkout. Revisa la consola.", "danger")
            return redirect(url_for("main"))

    except Exception as e:
        print(" Error al crear la preferencia:", e)
        traceback.print_exc()
        flash("Error al generar el checkout. Revisa la consola.", "danger")
        return redirect(url_for("main"))


@app.route("/pago_exitoso")
def pago_exitoso():
    return render_template(
        "resultado_pago.html", mensaje="Pago aprobado! Gracias por tu compra."
    )


@app.route("/pago_fallido")
def pago_fallido():
    return render_template(
        "resultado_pago.html",
        mensaje="El pago no fue completado. Intenta nuevamente.",
    )


@app.route("/pago_pendiente")
def pago_pendiente():
    return render_template(
        "resultado_pago.html", mensaje="El pago está pendiente de confirmación."
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
