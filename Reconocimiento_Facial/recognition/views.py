from django.shortcuts import render, redirect
from .forms import usernameForm, DateForm, UsernameAndDateForm, DateForm_2
from django.contrib import messages
from django.contrib.auth.models import User
import cv2
import dlib
import imutils
from imutils import face_utils
from imutils.video import VideoStream
from imutils.face_utils import rect_to_bb
from imutils.face_utils import FaceAligner
import time
from reconocimiento_facial.settings import BASE_DIR
import os
import face_recognition
from face_recognition.face_recognition_cli import image_files_in_folder
import pickle
from sklearn.preprocessing import LabelEncoder
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
import numpy as np
from django.contrib.auth.decorators import login_required
import matplotlib as mpl
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import datetime
from django_pandas.io import read_frame
from users.models import Present, Time
import seaborn as sns
import pandas as pd
from django.db.models import Count
#import mpld3
from pandas.plotting import register_matplotlib_converters
from matplotlib import rcParams
import math
from .forms import Configuracion, Asignacion_Horario
from users.models import Horarios, Asignacion
from .funciones import validate_time_entry, validate_time_exit


mpl.use('Agg')


# Funcion global util
def username_present(username):
    if User.objects.filter(username=username).exists():
        return True

    return False


def create_dataset(username):
    id = username
    if (os.path.exists('face_recognition_data/training_dataset/{}/'.format(id)) == False):
        os.makedirs('face_recognition_data/training_dataset/{}/'.format(id))
    directory = 'face_recognition_data/training_dataset/{}/'.format(id)

    # Deteccioon facial
    # Carga del HOG de la deteccion facial y del modelo predictor

    print("[INFO] Cargando el detector Facial")
    detector = dlib.get_frontal_face_detector()
    # Se anade el predictor
    predictor = dlib.shape_predictor(
        'face_recognition_data/shape_predictor_68_face_landmarks.dat')
    fa = FaceAligner(predictor, desiredFaceWidth=96)
    # caputra imagenes desde la camara, las procesa y detecta los rostros
    # Inicia la captura por video
    print("[INFO] Inicializando Video Captura")
    vs = VideoStream(src=1).start()
    # Con src podemos cambiar el dispositivo de entrada 0 para una camara unica y
    # n valores dependiendo del nuemro de la camara a usarse

    # El identificador
    # Aqui se pondra el id y se guardara el rostro de acuerdo al id

    # Contador del etiquetado del dataset
    sampleNum = 0
    # Capturando los rostros uno por uno y la deteccion de rostros mientras se muestra en una ventana
    while (True):
        # Capturando imagen
        # vs para cada frame
        frame = vs.read()
        # redimencionado de la imagen
        frame = imutils.resize(frame, width=800)
        # la imagen que se retorna por camara es a color, para el clasificador se necesita una imagen a escala a grises
        # para convertir de color a escala a grises
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # para guardar los rostros
        # Se detectaran todas las imagenes en el frame y estas retornaran las coordenadas de los rostros.
        # Se toma una imagen y un parametro para medir el resultado
        faces = detector(gray_frame, 0)
        # dentro de la variable 'faces' puede haber multiples rostros entonces tenemos que capturar cada uno de ellos
        # y dibujar un rectangulo alrededor

        for face in faces:
            print("iniciando ")
            (x, y, w, h) = face_utils.rect_to_bb(face)

            face_aligned = fa.align(frame, gray_frame, face)
            # Siempre que el programa capture rostros, los escribira como si fueran una carpeta
            # Antes de capturar los rostros, necesitamos hacerle saber al script de quien es cada rostro
            # Para eo necesitamos un identificador
            # ahora que se ha capturado un rostro, necesitamos transformalo en un archivo
            sampleNum = sampleNum+1
            # Se guarda la imagen en el dataset, pero solo el rostro, cortando el resto de la captura de imagen

            if face is None:
                print("no se identifican rostros")
                continue

            cv2.imwrite(directory+'/'+str(sampleNum)+'.jpg', face_aligned)
            face_aligned = imutils.resize(face_aligned, width=400)
            # @params el punto inicial del rectangulo sera x e y y
            # @params el punto final sera x+width e y+height
            # @params conjunto va el color del marco
            # @params espesor del marco
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 1)
            cv2.waitKey(50)

        # Se muestra la imagen en otra ventana
        # Se crea una ventana con el nombre Rostro y con una imgaen img
        cv2.imshow("Anadir Imagenes", frame)
        # Antes de cerrar la ventana necesitamos dar un comando de espera, por que si no open cv no funcionara
        # @params una millonesima de segundo en un segundo
        cv2.waitKey(1)
        # Para salir del bucle
        if (sampleNum > 150):
            break

    # Interrupcion del video
    vs.stop()
    # eliminacion de todas las ventanas
    cv2.destroyAllWindows()


def predict(face_aligned, svc, threshold=0.7):
    face_encodings = np.zeros((1, 128))
    try:
        x_face_locations = face_recognition.face_locations(face_aligned)
        faces_encodings = face_recognition.face_encodings(
            face_aligned, known_face_locations=x_face_locations)
        if (len(faces_encodings) == 0):
            return ([-1], [0])

    except:

        return ([-1], [0])

    prob = svc.predict_proba(faces_encodings)
    result = np.where(prob[0] == np.amax(prob[0]))
    if (prob[0][result[0]] <= threshold):
        return ([-1], prob[0][result[0]])

    return (result[0], prob[0][result[0]])


def vizualize_Data(embedded, targets,):

    X_embedded = TSNE(n_components=2).fit_transform(embedded)

    for i, t in enumerate(set(targets)):
        idx = targets == t
        plt.scatter(X_embedded[idx, 0], X_embedded[idx, 1], label=t)

    plt.legend(bbox_to_anchor=(1, 1))
    rcParams.update({'figure.autolayout': True})
    plt.tight_layout()
    plt.savefig(
        './recognition/static/recognition/img/training_visualisation.png')
    plt.close()


def update_attendance_in_db_in(present):
    today = datetime.date.today()
    time = datetime.datetime.now()

    for person in present:
        print("person in present")
        print(person)
        user = User.objects.get(username=person)
        try:
            qs = Present.objects.get(user=user, date=today, time=time)
        except:
            qs = None

        if qs is None:
            if present[person] == True:
                a = Present(user=user, date=today, time=time, present=True)
                # verifica el horario y tiempo
                # if validate_time_entry(user):
                print('primer save')
                a.save()
                # else:
                # print('atraso')

            else:
                a = Present(user=user, date=today, time=time, present=False)
                print('Segundo save')
                a.save()

        else:
            if present[person] == True:
                qs.present = True
                qs.save(update_fields=['present'])
                #a = Present(user=user, date=today, time=time, present=True)
                # a.save()

        if present[person] == True:
            a = Time(user=user, date=today, time=time, out=False)
            a.save()


def update_attendance_in_db_out(present):
    today = datetime.date.today()
    time = datetime.datetime.now()

    for person in present:
        user = User.objects.get(username=person)
        if present[person] == True:
            a = Time(user=user, date=today, time=time, out=True)
            print(a)
            # if validate_time_exit(user):
            a.save()
            # else:
            #    print('atraso')


def check_validity_times(times_all):

    if (len(times_all) > 0):
        sign = times_all.first().out
    else:
        sign = True
    times_in = times_all.filter(out=False)
    times_out = times_all.filter(out=True)
    if (len(times_in) != len(times_out)):
        sign = True
    break_hourss = 0
    if (sign == True):
        check = False
        break_hourss = 0
        return (check, break_hourss)
    prev = True
    prev_time = times_all.first().time

    for obj in times_all:
        curr = obj.out
        if (curr == prev):
            check = False
            break_hourss = 0
            return (check, break_hourss)
        if (curr == False):
            curr_time = obj.time
            to = curr_time
            ti = prev_time
            break_time = ((to-ti).total_seconds())/3600
            break_hourss += break_time

        else:
            prev_time = obj.time

        prev = curr

    return (True, break_hourss)


def convert_hours_to_hours_mins(hours):

    h = int(hours)
    hours -= h
    m = hours*60
    m = math.ceil(m)
    return str(str(h) + " hrs " + str(m) + "  mins")


# used
# este es
def hours_vs_date_given_employee(present_qs, time_qs, admin=True):
    register_matplotlib_converters()
    df_hours = []
    df_break_hours = []
    qs = present_qs
    for obj in qs:
        print(obj.id)
        date = obj.date

        times_in = time_qs.filter(time=obj.time).filter(
            out=False).order_by('time')
        print('times_in')
        print(times_in)
        times_out = time_qs.filter(time__gt=obj.time).filter(
            out=True).order_by('time')
        times_all = time_qs.filter(date=date).order_by('time')
        obj.time_in = None
        obj.time_out = None
        obj.hours = 0
        obj.break_hours = 0
        if (len(times_in) > 0):
            print('controla la entrada')
            obj.time_in = times_in.last().time

        if (len(times_out) > 0):
            print('controla salida')
            obj.time_out = times_out[0].time

        else:
            print("No hay salida para el present")

        if (obj.time_in is not None and obj.time_out is not None):
            ti = obj.time_in
            to = obj.time_out
            hours = ((to-ti).total_seconds())/3600
            obj.hours = hours

        else:
            obj.hours = 0

        (check, break_hourss) = check_validity_times(times_all)
        if check:
            obj.break_hours = break_hourss

        else:
            obj.break_hours = 0

        df_hours.append(obj.hours)
        df_break_hours.append(obj.break_hours)
        obj.hours = convert_hours_to_hours_mins(obj.hours)
        obj.break_hours = convert_hours_to_hours_mins(obj.break_hours)

    df = read_frame(qs)

    df["hours"] = df_hours
    df["break_hours"] = df_break_hours

    print(df)

    sns.barplot(data=df, x='date', y='hours')
    plt.xticks(rotation='vertical')
    rcParams.update({'figure.autolayout': True})
    plt.tight_layout()
    if (admin):
        plt.savefig(
            './recognition/static/recognition/img/attendance_graphs/hours_vs_date/1.png')
        plt.close()
    else:
        plt.savefig(
            './recognition/static/recognition/img/attendance_graphs/employee_login/1.png')
        plt.close()

    return qs


# used
def hours_vs_employee_given_date(present_qs, time_qs):
    register_matplotlib_converters()
    df_hours = []
    df_break_hours = []
    df_username = []
    qs = present_qs

    for obj in qs:
        user = obj.user
        times_in = time_qs.filter(user=user).filter(out=False)
        times_out = time_qs.filter(user=user).filter(out=True)
        times_all = time_qs.filter(user=user)
        obj.time_in = None
        obj.time_out = None
        obj.hours = 0
        obj.hours = 0
        if (len(times_in) > 0):
            obj.time_in = times_in.first().time
        if (len(times_out) > 0):
            obj.time_out = times_out.last().time
        if (obj.time_in is not None and obj.time_out is not None):
            ti = obj.time_in
            to = obj.time_out
            hours = ((to-ti).total_seconds())/3600
            obj.hours = hours
        else:
            obj.hours = 0
        (check, break_hourss) = check_validity_times(times_all)
        if check:
            obj.break_hours = break_hourss

        else:
            obj.break_hours = 0

        df_hours.append(obj.hours)
        df_username.append(user.username)
        df_break_hours.append(obj.break_hours)
        obj.hours = convert_hours_to_hours_mins(obj.hours)
        obj.break_hours = convert_hours_to_hours_mins(obj.break_hours)

    df = read_frame(qs)
    df['hours'] = df_hours
    df['username'] = df_username
    df["break_hours"] = df_break_hours

    sns.barplot(data=df, x='username', y='hours')
    plt.xticks(rotation='vertical')
    rcParams.update({'figure.autolayout': True})
    plt.tight_layout()
    plt.savefig(
        './recognition/static/recognition/img/attendance_graphs/hours_vs_employee/1.png')
    plt.close()
    return qs


def total_number_employees():
    qs = User.objects.all()
    return (len(qs) - 1)
    # -1 to account for admin


def employees_present_today():
    today = datetime.date.today()
    qs = Present.objects.filter(date=today).filter(present=True)
    return len(qs)


# used
def this_week_emp_count_vs_date():
    today = datetime.date.today()
    some_day_last_week = today-datetime.timedelta(days=7)
    monday_of_last_week = some_day_last_week - \
        datetime.timedelta(days=(some_day_last_week.isocalendar()[2] - 1))
    monday_of_this_week = monday_of_last_week + datetime.timedelta(days=7)
    qs = Present.objects.filter(
        date__gte=monday_of_this_week).filter(date__lte=today)
    str_dates = []
    emp_count = []
    str_dates_all = []
    emp_cnt_all = []
    cnt = 0

    for obj in qs:
        date = obj.date
        str_dates.append(str(date))
        qs = Present.objects.filter(date=date).filter(present=True)
        emp_count.append(len(qs))

    while (cnt < 5):

        date = str(monday_of_this_week+datetime.timedelta(days=cnt))
        cnt += 1
        str_dates_all.append(date)
        if (str_dates.count(date)) > 0:
            idx = str_dates.index(date)

            emp_cnt_all.append(emp_count[idx])
        else:
            emp_cnt_all.append(0)

    df = pd.DataFrame()
    df["date"] = str_dates_all
    df["Number of employees"] = emp_cnt_all

    sns.lineplot(data=df, x='date', y='Number of employees')
    plt.savefig(
        './recognition/static/recognition/img/attendance_graphs/this_week/1.png')
    plt.close()


# used
def last_week_emp_count_vs_date():
    today = datetime.date.today()
    some_day_last_week = today-datetime.timedelta(days=7)
    monday_of_last_week = some_day_last_week - \
        datetime.timedelta(days=(some_day_last_week.isocalendar()[2] - 1))
    monday_of_this_week = monday_of_last_week + datetime.timedelta(days=7)
    qs = Present.objects.filter(date__gte=monday_of_last_week).filter(
        date__lt=monday_of_this_week)
    str_dates = []
    emp_count = []

    str_dates_all = []
    emp_cnt_all = []
    cnt = 0

    for obj in qs:
        date = obj.date
        str_dates.append(str(date))
        qs = Present.objects.filter(date=date).filter(present=True)
        emp_count.append(len(qs))

    while (cnt < 5):

        date = str(monday_of_last_week+datetime.timedelta(days=cnt))
        cnt += 1
        str_dates_all.append(date)
        if (str_dates.count(date)) > 0:
            idx = str_dates.index(date)

            emp_cnt_all.append(emp_count[idx])

        else:
            emp_cnt_all.append(0)

    df = pd.DataFrame()
    df["date"] = str_dates_all
    df["emp_count"] = emp_cnt_all

    sns.lineplot(data=df, x='date', y='emp_count')
    plt.savefig(
        './recognition/static/recognition/img/attendance_graphs/last_week/1.png')
    plt.close()


# Create your views here.
def home(request):

    return render(request, 'recognition/home.html')


@login_required
def dashboard(request):
    user = request.user
    usern = request.user.username
    print(validate_time_entry(user), ' ' + usern)
    print(validate_time_exit(user), " " + usern)

    if (request.user.username == 'admin'):
        print("admin")
        return render(request, 'recognition/admin_dashboard.html')
    else:
        print("not admin")

        return render(request, 'recognition/employee_dashboard.html')


@login_required
def add_photos(request):
    if request.user.username != 'admin':
        return redirect('not-authorised')
    if request.method == 'POST':
        form = usernameForm(request.POST)
        data = request.POST.copy()
        username = data.get('username')
        if username_present(username):
            create_dataset(username)
            messages.success(request, f'Dataset Creado')
            return redirect('add-photos')
        else:
            messages.warning(
                request, f'No se encuentra este nombre de usuario por favor realize el registro.')
            return redirect('dashboard')

    else:

        form = usernameForm()
        return render(request, 'recognition/add_photos.html', {'form': form})


def mark_your_attendance(request):

    detector = dlib.get_frontal_face_detector()

    # Anade el predictor con los 68 puntos princpales del rostro
    predictor = dlib.shape_predictor(
        'face_recognition_data/shape_predictor_68_face_landmarks.dat')
    svc_save_path = "face_recognition_data/svc.sav"

    with open(svc_save_path, 'rb') as f:
        svc = pickle.load(f)
    fa = FaceAligner(predictor, desiredFaceWidth=96)
    encoder = LabelEncoder()
    encoder.classes_ = np.load('face_recognition_data/classes.npy')

    faces_encodings = np.zeros((1, 128))
    no_of_faces = len(svc.predict_proba(faces_encodings)[0])
    count = dict()
    present = dict()
    log_time = dict()
    start = dict()
    for i in range(no_of_faces):
        count[encoder.inverse_transform([i])[0]] = 0
        present[encoder.inverse_transform([i])[0]] = False

    vs = VideoStream(src=1).start()

    sampleNum = 0

    while (True):

        frame = vs.read()

        frame = imutils.resize(frame, width=800)

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = detector(gray_frame, 0)

        for face in faces:
            print("INFO : dentro del bucle ")
            (x, y, w, h) = face_utils.rect_to_bb(face)

            face_aligned = fa.align(frame, gray_frame, face)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 1)

            (pred, prob) = predict(face_aligned, svc)

            if (pred != [-1]):

                person_name = encoder.inverse_transform(np.ravel([pred]))[0]
                pred = person_name
                if count[pred] == 0:
                    start[pred] = time.time()

                    count[pred] = count.get(pred, 0) + 1

                if count[pred] == 4 and (time.time()-start[pred]) > 1.2:
                    count[pred] = 0
                else:
                    present[pred] = True
                    log_time[pred] = datetime.datetime.now()
                    count[pred] = count.get(pred, 0) + 1
                    print(pred, present[pred], count[pred])
                cv2.putText(frame, str(person_name) + str(prob), (x+6,
                            y+h-6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            else:
                person_name = "desconocido"
                cv2.putText(frame, str(person_name), (x+6, y+h-6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Mostrando la imagen en una ventana
        # Se crea una ventana con el nombre de la accion y la accion necesaria para salir
        cv2.imshow("Marca tu entrada - Presiona q para salir", frame)
        # Antes de cerrar se necesita dar un compando de espera, caso contrario opencv no funcionara
        # @params with the millisecond of delay 1
        # @params con los millisegundos en un delay de 1
        # para salir del bucle
        key = cv2.waitKey(50) & 0xFF
        if (key == ord("q")):
            break

    # Para el stream
    vs.stop()

    # Se sale de todas las ventanas
    cv2.destroyAllWindows()
    print("##############################")
    print(present)
    update_attendance_in_db_in(present)

    return redirect('home')


def mark_your_attendance_out(request):

    detector = dlib.get_frontal_face_detector()

    # Add path to the shape predictor ######CHANGE TO RELATIVE PATH LATER
    predictor = dlib.shape_predictor(
        'face_recognition_data/shape_predictor_68_face_landmarks.dat')
    svc_save_path = "face_recognition_data/svc.sav"

    with open(svc_save_path, 'rb') as f:
        svc = pickle.load(f)
    fa = FaceAligner(predictor, desiredFaceWidth=96)
    encoder = LabelEncoder()
    encoder.classes_ = np.load('face_recognition_data/classes.npy')

    faces_encodings = np.zeros((1, 128))
    no_of_faces = len(svc.predict_proba(faces_encodings)[0])
    count = dict()
    present = dict()
    log_time = dict()
    start = dict()
    for i in range(no_of_faces):
        count[encoder.inverse_transform([i])[0]] = 0
        present[encoder.inverse_transform([i])[0]] = False

    vs = VideoStream(src=1).start()

    sampleNum = 0

    while (True):

        frame = vs.read()

        frame = imutils.resize(frame, width=800)

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = detector(gray_frame, 0)

        for face in faces:
            print("INFO : dentro del bucle")
            (x, y, w, h) = face_utils.rect_to_bb(face)

            face_aligned = fa.align(frame, gray_frame, face)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 1)

            (pred, prob) = predict(face_aligned, svc)

            if (pred != [-1]):

                person_name = encoder.inverse_transform(np.ravel([pred]))[0]
                pred = person_name
                if count[pred] == 0:
                    start[pred] = time.time()
                    count[pred] = count.get(pred, 0) + 1

                if count[pred] == 4 and (time.time()-start[pred]) > 1.5:
                    count[pred] = 0
                else:
                    # if count[pred] == 4 and (time.time()-start) <= 1.5:
                    present[pred] = True
                    log_time[pred] = datetime.datetime.now()
                    count[pred] = count.get(pred, 0) + 1
                    print(pred, present[pred], count[pred])
                cv2.putText(frame, str(person_name) + str(prob), (x+6,
                            y+h-6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            else:
                person_name = "desconocido"
                cv2.putText(frame, str(person_name), (x+6, y+h-6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # cv2.putText()
            # Before continuing to the next loop, I want to give it a little pause
            # waitKey of 100 millisecond
            # cv2.waitKey(50)

        # Showing the image in another window
        # Creates a window with window name "Face" and with the image img
        cv2.imshow("Marca tu salida - Presiona q para salir", frame)
        # Before closing it we need to give a wait command, otherwise the open cv wont work
        # @params with the millisecond of delay 1
        # cv2.waitKey(1)
        # To get out of the loop
        key = cv2.waitKey(50) & 0xFF
        if (key == ord("q")):
            break

    # Stoping the videostream
    vs.stop()

    # destroying all the windows
    cv2.destroyAllWindows()
    print("mark out")

    update_attendance_in_db_out(present)
    return redirect('home')


@login_required
def train(request):
    if request.user.username != 'admin':
        return redirect('not-authorised')

    training_dir = 'face_recognition_data/training_dataset'

    count = 0
    for person_name in os.listdir(training_dir):
        curr_directory = os.path.join(training_dir, person_name)
        if not os.path.isdir(curr_directory):
            continue
        for imagefile in image_files_in_folder(curr_directory):
            count += 1

    X = []
    y = []
    i = 0

    for person_name in os.listdir(training_dir):
        print(str(person_name))
        curr_directory = os.path.join(training_dir, person_name)
        if not os.path.isdir(curr_directory):
            continue
        for imagefile in image_files_in_folder(curr_directory):
            print(str(imagefile))
            image = cv2.imread(imagefile)
            try:
                X.append((face_recognition.face_encodings(image)[0]).tolist())

                y.append(person_name)
                i += 1
            except:
                print("removido")
                os.remove(imagefile)

    targets = np.array(y)
    encoder = LabelEncoder()
    encoder.fit(y)
    y = encoder.transform(y)
    X1 = np.array(X)
    print("shape: " + str(X1.shape))
    np.save('face_recognition_data/classes.npy', encoder.classes_)
    svc = SVC(kernel='linear', probability=True)
    svc.fit(X1, y)
    svc_save_path = "face_recognition_data/svc.sav"
    with open(svc_save_path, 'wb') as f:
        pickle.dump(svc, f)

    vizualize_Data(X1, targets)

    messages.success(request, f'Entrenamiento completado')

    return render(request, "recognition/train.html")


@login_required
def not_authorised(request):
    return render(request, 'recognition/not_authorised.html')


@login_required
def view_attendance_home(request):
    total_num_of_emp = total_number_employees()
    emp_present_today = employees_present_today()
    this_week_emp_count_vs_date()
    last_week_emp_count_vs_date()
    return render(request, "recognition/view_attendance_home.html", {'total_num_of_emp': total_num_of_emp, 'emp_present_today': emp_present_today})


@login_required
def view_attendance_date(request):
    if request.user.username != 'admin':
        return redirect('not-authorised')
    qs = None
    time_qs = None
    present_qs = None

    if request.method == 'POST':
        form = DateForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data.get('date')
            print("date:" + str(date))
            time_qs = Time.objects.filter(date=date)
            present_qs = Present.objects.filter(date=date)
            if (len(time_qs) > 0 or len(present_qs) > 0):
                qs = hours_vs_employee_given_date(present_qs, time_qs)

                return render(request, 'recognition/view_attendance_date.html', {'form': form, 'qs': qs})
            else:
                messages.warning(
                    request, f'No existen datos para la fecha seleccionada.')
                return redirect('view-attendance-date')

    else:

        form = DateForm()
        return render(request, 'recognition/view_attendance_date.html', {'form': form, 'qs': qs})


@login_required
def view_attendance_employee(request):
    if request.user.username != 'admin':
        return redirect('not-authorised')
    time_qs = None
    present_qs = None
    qs = None
    ('######')
    if request.method == 'POST':
        form = UsernameAndDateForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data.get('username')
            #courses = form.cleaned_data.get('course')
            if username_present(username):

                u = User.objects.get(username=username)
                #courses = Horarios.objects.all().filter(user=u)

                # for values_entry in courses:
                #    for course in values_entry.horas_asignadas.all().order_by('asignatura'):
                #        course_qs = course.asignatura
                #        print(course_qs)

                time_qs = Time.objects.filter(user=u)
                present_qs = Present.objects.filter(user=u)
                date_from = form.cleaned_data.get('date_from')
                date_to = form.cleaned_data.get('date_to')

                if date_to < date_from:
                    messages.warning(request, f'seleccion de fecha incorrecta')
                    return redirect('view-attendance-employee')
                else:

                    time_qs = time_qs.filter(date__gte=date_from).filter(
                        date__lte=date_to).order_by('-date')
                    present_qs = present_qs.filter(date__gte=date_from).filter(
                        date__lte=date_to).order_by('-date')

                    if (len(time_qs) > 0 or len(present_qs) > 0):
                        qs = hours_vs_date_given_employee(
                            present_qs, time_qs, admin=True)
                        print("qs lane 904")
                        print(qs)
                        return render(request, 'recognition/view_attendance_employee.html', {'form': form, 'qs': qs})
                    else:
                        #print("inside qs is None")
                        messages.warning(
                            request, f'No hay records en las fechas seleccionadas.')
                        return redirect('view-attendance-employee')

            else:
                print("invalid username")
                messages.warning(request, f'No se encuentra este usuario')
                return redirect('view-attendance-employee')

    else:

        form = UsernameAndDateForm()
        return render(request, 'recognition/view_attendance_employee.html', {'form': form, 'qs': qs})


@login_required
def view_my_attendance_employee_login(request):
    if request.user.username == 'admin':
        return redirect('not-authorised')
    qs = None
    time_qs = None
    present_qs = None
    if request.method == 'POST':
        form = DateForm_2(request.POST)
        if form.is_valid():
            u = request.user
            time_qs = Time.objects.filter(user=u)
            present_qs = Present.objects.filter(user=u)
            date_from = form.cleaned_data.get('date_from')
            date_to = form.cleaned_data.get('date_to')
            if date_to < date_from:
                messages.warning(request, f'seleccion invalida')
                return redirect('view-my-attendance-employee-login')
            else:

                time_qs = time_qs.filter(date__gte=date_from).filter(
                    date__lte=date_to).order_by('-date')
                present_qs = present_qs.filter(date__gte=date_from).filter(
                    date__lte=date_to).order_by('-date')

                if (len(time_qs) > 0 or len(present_qs) > 0):
                    qs = hours_vs_date_given_employee(
                        present_qs, time_qs, admin=False)
                    return render(request, 'recognition/view_my_attendance_employee_login.html', {'form': form, 'qs': qs})
                else:

                    messages.warning(
                        request, f'No hay datos en esta seleccion')
                    return redirect('view-my-attendance-employee-login')
    else:

        form = DateForm_2()
        return render(request, 'recognition/view_my_attendance_employee_login.html', {'form': form, 'qs': qs})


@login_required
def view_configuracion_horarios(request):
    if request.user.username != 'admin':
        return redirect('not-authorised')

    if request.method == 'POST':
        form = Configuracion(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            horas = form.cleaned_data.get('horas_asignadas')
            horario = Horarios(user=user)
            horario.save()
            for horas in horas:

                horario.horas_asignadas.add(horas)

            return redirect('dashboard')

    else:

        form = Configuracion()
        return render(request, 'recognition/view_configuracion_horarios.html', {'form': form})


@login_required
def mostrar_horarios(request):
    if request.user.username != 'admin':
        return redirect('not-authorised')

    if request.method == 'POST':
        form = Asignacion_Horario(request.POST)
        if form.is_valid():
            dia = form.cleaned_data['user']
            hora_inicio = form.cleaned_data.get('horas_inicio')
            hora_fin = form.cleaned_data.get('horas_fin')
            asignatura = form.cleaned_data.get('asignatura')

            asigna_horario = Asignacion(
                dia=dia, hora_inicio=hora_inicio, hora_fin=hora_fin, asignatura=asignatura)
            asigna_horario.save()
            return redirect('dashboard')

    else:

        form = Asignacion_Horario()
        horarios = Asignacion.objects.all()
        return render(request, 'recognition/mostrar_horarios.html', {'form': form, 'horarios': horarios})
