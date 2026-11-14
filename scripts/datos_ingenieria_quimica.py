"""Datos reales del programa de Ingeniería Química (UNAL, sede Manizales).

Fuentes:
- Malla 2016: "Plan de estudios. Acuerdo 252 de 2016 del Consejo de Facultad".
- Malla 2026: propuesta "Malla_13_05_2026" (vigente).
- Créditos de la malla 2016 verificados contra el resumen de créditos de las
  historias académicas reales (fund. obligatoria 62, disciplinar obligatoria 55,
  optativas 21, libre elección 36, nivelación 12 -> 192).

PENDIENTES DE CONFIRMAR CON LA UNIVERSIDAD (están marcados en el Excel):
- Las materias nuevas aparecen como "XXXXXX" en la malla 2026: se usan códigos
  temporales NUEVO01..NUEVO08 hasta que tengan código oficial.
- Las equivalencias se cargan como "propuesta".
- El código de Trabajo de Grado en la malla 2026 no aparece en el PDF; se asume 4100882.

Los estudiantes son de PRUEBA y están anonimizados (no son datos reales de personas).
"""
from __future__ import annotations

OB, OP, LE, NIV = "obligatoria", "optativa", "electiva", "nivelacion"
CS, FIS, DIS = "ciencias_sociales", "fisica", "disciplinar"

# (semestre, codigo, nombre, creditos, tipo, grupo, observacion)
MALLA_2016 = [
    (1, "1000004", "Cálculo Diferencial", 4, OB, "", ""),
    (1, "4100925", "Programación en Ingeniería", 2, OB, "", ""),
    (1, "4100839", "Química General I", 3, OB, "", ""),
    (1, "4100826", "Introducción a la Ingeniería Química", 2, OB, "", ""),
    (1, "OPT-CS", "Optativa en Ciencias Sociales", 2, OP, CS, ""),
    (1, "1000044", "Inglés I", 3, NIV, "", ""),
    (2, "1000005", "Cálculo Integral", 4, OB, "", ""),
    (2, "1000019", "Física: Mecánica", 4, OB, "", ""),
    (2, "4100831", "Laboratorio de Química General", 2, OB, "", ""),
    (2, "4100840", "Química General II", 3, OB, "", ""),
    (2, "1000003", "Álgebra Lineal", 4, OB, "", ""),
    (2, "LE-01", "Libre elección", 4, LE, "", ""),
    (2, "1000045", "Inglés II", 3, NIV, "", ""),
    (3, "1000006", "Cálculo Vectorial", 4, OB, "", ""),
    (3, "OPT-FIS", "Optativa de Física", 4, OP, FIS, ""),
    (3, "4100830", "Laboratorio de Química Analítica", 2, OB, "", ""),
    (3, "4100838", "Química Analítica", 3, OB, "", ""),
    (3, "4100930", "Termodinámica I", 4, OB, "", ""),
    (3, "1000046", "Inglés III", 3, NIV, "", ""),
    (4, "1000007", "Ecuaciones Diferenciales", 4, OB, "", ""),
    (4, "4100926", "Biología Celular y Microbiología", 2, OB, "", ""),
    (4, "4100923", "Mecánica de Fluidos", 3, OB, "", ""),
    (4, "4100841", "Química Orgánica", 3, OB, "", ""),
    (4, "4100931", "Termodinámica II", 4, OB, "", ""),
    (4, "4100836", "Principios de los Procesos Químicos", 3, OB, "", ""),
    (4, "1000047", "Inglés IV", 3, NIV, "", ""),
    (5, "4100928", "Métodos Numéricos Aplicados a Ingeniería Química", 3, OB, "", ""),
    (5, "4100890", "Bioquímica", 3, OB, "", ""),
    (5, "4100932", "Fenómenos de Transferencia", 4, OB, "", ""),
    (5, "4100832", "Laboratorio de Química Orgánica", 2, OB, "", ""),
    (5, "1000013", "Probabilidad y Estadística", 3, OB, "", ""),
    (5, "4100924", "Operaciones con Sólidos", 3, OB, "", ""),
    (6, "4100921", "Fundamentos de Economía", 2, OB, "", ""),
    (6, "4100837", "Procesos de Separación", 4, OB, "", ""),
    (6, "4100929", "Procesos de Transferencia de Calor", 3, OB, "", ""),
    (6, "4100820", "Cinética y Catálisis", 2, OB, "", ""),
    (6, "OPT-DIS-1", "Optativa profesional I", 3, OP, DIS, ""),
    (6, "LE-02", "Libre elección", 4, LE, "", ""),
    (7, "4100842", "Humanidades para Ingenierías", 2, OB, "", ""),
    (7, "4100828", "Laboratorio de Ingeniería Química I", 2, OB, "", ""),
    (7, "4100823", "Ingeniería de las Reacciones Químicas", 3, OB, "", ""),
    (7, "OPT-DIS-2", "Optativa profesional II", 3, OP, DIS, ""),
    (7, "LE-03", "Libre elección", 4, LE, "", ""),
    (7, "LE-04", "Libre elección", 4, LE, "", ""),
    (8, "4100825", "Ingeniería de Procesos I", 3, OB, "", ""),
    (8, "4100829", "Laboratorio de Ingeniería Química II", 2, OB, "", ""),
    (8, "4100844", "Control de Procesos", 4, OB, "", ""),
    (8, "OPT-DIS-3", "Optativa de profundización I", 3, OP, DIS, ""),
    (8, "LE-05", "Libre elección", 4, LE, "", ""),
    (9, "4101192", "Formulación y Evaluación de Proyectos", 3, OB, "", ""),
    (9, "4100927", "Ingeniería de Procesos II", 3, OB, "", ""),
    (9, "4100922", "Taller de Procesos Productivos", 3, OB, "", ""),
    (9, "OPT-DIS-4", "Optativa de profundización II", 3, OP, DIS, ""),
    (9, "LE-06", "Libre elección", 4, LE, "", ""),
    (9, "LE-07", "Libre elección", 4, LE, "", ""),
    (10, "4100821", "Diseño de Plantas y Equipos", 3, OB, "", ""),
    (10, "4100882", "Trabajo de Grado", 6, OB, "", ""),
    (10, "OPT-DIS-5", "Optativa de profundización III", 3, OP, DIS, ""),
    (10, "LE-08", "Libre elección", 4, LE, "", ""),
    (10, "LE-09", "Libre elección", 4, LE, "", ""),
]

SIN_CODIGO = "Código temporal: la malla 2026 la muestra como XXXXXX."

MALLA_2026 = [
    (1, "1000004", "Cálculo Diferencial", 4, OB, "", ""),
    (1, "1000003", "Álgebra Lineal", 4, OB, "", ""),
    (1, "4100826", "Introducción a la Ingeniería Química", 2, OB, "", ""),
    (1, "4100842", "Humanidades para Ingeniería", 2, OB, "", ""),
    (1, "NUEVO01", "Química General", 3, OB, "", SIN_CODIGO),
    (1, "4100831", "Laboratorio de Química General", 2, OB, "", ""),
    (2, "1000005", "Cálculo Integral", 4, OB, "", ""),
    (2, "1000019", "Física: Mecánica", 4, OB, "", ""),
    (2, "OPT-CS", "Optativa en Ciencias Sociales", 2, OP, CS, ""),
    (2, "4100841", "Química Orgánica", 3, OB, "", ""),
    (2, "4100832", "Laboratorio de Química Orgánica", 2, OB, "", ""),
    (2, "1000044", "Inglés I", 3, NIV, "", ""),
    (3, "1000007", "Ecuaciones Diferenciales", 4, OB, "", ""),
    (3, "1000017", "Física: Electricidad y Magnetismo", 4, OB, "", ""),
    (3, "4100930", "Termodinámica I", 4, OB, "", ""),
    (3, "4100838", "Química Analítica", 3, OB, "", ""),
    (3, "4100830", "Laboratorio de Química Analítica", 2, OB, "", ""),
    (3, "1000045", "Inglés II", 3, NIV, "", ""),
    (4, "4100923", "Mecánica de Fluidos", 4, OB, "", ""),
    (4, "NUEVO02", "Balances de Materia y Energía", 4, OB, "", SIN_CODIGO),
    (4, "4100931", "Termodinámica II", 4, OB, "", ""),
    (4, "NUEVO03", "Laboratorio de Fisicoquímica", 3, OB, "", SIN_CODIGO),
    (4, "NUEVO04", "Fundamentos de Biotecnología", 3, OB, "", SIN_CODIGO),
    (4, "1000046", "Inglés III", 3, NIV, "", ""),
    (5, "NUEVO05", "Programación y Métodos Numéricos", 4, OB, "", SIN_CODIGO),
    (5, "NUEVO06", "Transferencia de Masa I", 4, OB, "", SIN_CODIGO),
    (5, "4100929", "Transferencia de Calor", 4, OB, "", ""),
    (5, "OPT-DIS-1", "Optativa profesional / disciplinar I", 3, OP, DIS, ""),
    (5, "LE-01", "Libre elección", 3, LE, "", ""),
    (5, "LE-02", "Libre elección", 3, LE, "", ""),
    (5, "1000047", "Inglés IV", 3, NIV, "", ""),
    (6, "4100828", "Laboratorio de Ingeniería Química I", 3, OB, "", ""),
    (6, "NUEVO07", "Transferencia de Masa II", 4, OB, "", SIN_CODIGO),
    (6, "OPT-DIS-2", "Optativa profesional / disciplinar II", 3, OP, DIS, ""),
    (6, "LE-03", "Libre elección", 3, LE, "", ""),
    (6, "LE-04", "Libre elección", 3, LE, "", ""),
    (6, "LE-05", "Libre elección", 3, LE, "", ""),
    (7, "4100829", "Laboratorio de Ingeniería Química II", 3, OB, "", ""),
    (7, "4100823", "Ingeniería de las Reacciones Químicas", 4, OB, "", ""),
    (7, "OPT-DIS-3", "Optativa profesional / disciplinar III", 3, OP, DIS, ""),
    (7, "LE-06", "Libre elección", 3, LE, "", ""),
    (7, "LE-07", "Libre elección", 3, LE, "", ""),
    (8, "4100825", "Ingeniería de Procesos I", 4, OB, "", ""),
    (8, "4100844", "Control de Procesos", 3, OB, "", ""),
    (8, "OPT-DIS-4", "Optativa profesional / disciplinar IV", 3, OP, DIS, ""),
    (8, "LE-08", "Libre elección", 3, LE, "", ""),
    (8, "LE-09", "Libre elección", 3, LE, "", ""),
    (9, "4100922", "Taller de Procesos Productivos", 4, OB, "", ""),
    (9, "4100927", "Ingeniería de Procesos II", 4, OB, "", ""),
    (9, "NUEVO08", "Seguridad de Procesos Químicos", 4, OB, "", SIN_CODIGO),
    (9, "OPT-DIS-5", "Optativa profesional / disciplinar V", 3, OP, DIS, ""),
    (9, "LE-10", "Libre elección", 3, LE, "", ""),
    (9, "LE-11", "Libre elección", 3, LE, "", ""),
    (10, "4100882", "Trabajo de Grado", 6, OB, "", "Código por confirmar en la malla 2026."),
]

# (codigo_anterior, nombre_anterior, codigo_nuevo, nombre_nuevo, estado, observacion)
EQUIVALENCIAS = [
    ("4100839", "Química General I", "NUEVO01", "Química General", "propuesta",
     "Fusión: exige Química General I y II."),
    ("4100840", "Química General II", "NUEVO01", "Química General", "propuesta",
     "Fusión: exige Química General I y II."),
    ("4100925", "Programación en Ingeniería", "NUEVO05", "Programación y Métodos Numéricos", "propuesta",
     "Fusión: exige Programación en Ingeniería y Métodos Numéricos."),
    ("4100928", "Métodos Numéricos Aplicados a Ingeniería Química", "NUEVO05",
     "Programación y Métodos Numéricos", "propuesta",
     "Fusión: exige Programación en Ingeniería y Métodos Numéricos."),
    ("4100836", "Principios de los Procesos Químicos", "NUEVO02", "Balances de Materia y Energía", "propuesta", ""),
    ("4100932", "Fenómenos de Transferencia", "NUEVO06", "Transferencia de Masa I", "propuesta", ""),
    ("4100837", "Procesos de Separación", "NUEVO07", "Transferencia de Masa II", "propuesta", ""),
]

# (grupo, codigo, nombre) — catálogo de optativas (página 2 de la malla 2026).
# Las optativas del catálogo sin código (XXXXXX) no se incluyen todavía:
# Catálisis Ambiental, Energías Renovables, Tecnología en Manejo de Suelos,
# Biología de las Fermentaciones.
OPTATIVAS = [
    (CS, "4100682", "Expresiones y Creatividad"),
    (CS, "4100712", "Humanidades"),
    (CS, "4100570", "Sociología de la Industria y el Trabajo"),
    (CS, "4100684", "Sociología Industrial"),
    (CS, "4010199", "Ética y Empresa"),
    (FIS, "1000017", "Física: Electricidad y Magnetismo"),
    (FIS, "1000020", "Física: Oscilaciones, Ondas y Óptica"),
    (DIS, "4100722", "Generación de Energía Eléctrica"),
    (DIS, "4101191", "Dibujo Asistido por Computador"),
    (DIS, "4100820", "Cinética y Catálisis"),
    (DIS, "4100651", "Gestión de la Calidad"),
    (DIS, "4100584", "Higiene y Seguridad Industrial"),
    (DIS, "4100859", "Ingeniería de Materiales"),
    (DIS, "4101718", "Práctica Empresarial en Ingeniería Química"),
    (DIS, "4200134", "Emisión de Contaminantes Atmosféricos y Calidad del Aire"),
    (DIS, "4201056", "Herramientas de Simulación y Análisis de Datos en Calidad del Aire"),
    (DIS, "4200339", "Tecnología de Membranas y Sistemas Híbridos"),
    (DIS, "4200402", "Fisicoquímica Computacional"),
    (DIS, "4100822", "Fisicoquímica"),
    (DIS, "4200418", "Biotecnología Industrial"),
    (DIS, "4100890", "Bioquímica"),
    (DIS, "4200564", "Procesos Reactivos Heterogéneos"),
    (DIS, "4200642", "Aprovechamiento, Valorización y Tratamiento de Residuos"),
    (DIS, "4101228", "Ciencia de Alimentos"),
    (DIS, "4101194", "Introducción a los Polímeros"),
    (DIS, "4200337", "Calidad de Agua"),
    (DIS, "4200022", "Fundamentos de Aprovechamiento de Residuos"),
    (DIS, "4100824", "Ingeniería de Alimentos"),
    (DIS, "4101203", "Diseño de Plantas de Potabilización de Agua"),
    (DIS, "4101198", "Procesos de Polimerización"),
    (DIS, "4200078", "Sistemas de Aprovechamiento de Residuos"),
    (DIS, "4100843", "Tecnología de Alimentos"),
    (DIS, "4200338", "Ingeniería Ambiental"),
    (DIS, "4101199", "Procesos de Transformación de Polímeros"),
    (DIS, "4200079", "Simulación de Procesos en el Manejo de Residuos"),
]

# ---------------------------------------------------------------------------
# Estudiantes de prueba (anonimizados)
# ---------------------------------------------------------------------------
# (codigo, nombre, documento, correo, malla_version, estado)
ESTUDIANTES = [
    ("20242001", "Estudiante Prueba Uno", "1000000001", "prueba1@ejemplo.edu.co", "2016", "activo"),
    ("20221001", "Estudiante Prueba Dos", "1000000002", "prueba2@ejemplo.edu.co", "2016", "activo"),
    ("20261001", "Estudiante Prueba Tres", "1000000003", "prueba3@ejemplo.edu.co", "2026", "activo"),
]

A, R, C = "aprobada", "reprobada", "cursando"
B, Cd, O, T, L, E, P = (
    "fund_obligatoria", "disciplinar_obligatoria", "fund_optativa", "disciplinar_optativa",
    "libre_eleccion", "nivelacion", "trabajo_de_grado",
)

# (codigo_estudiante, codigo_materia, nombre_materia, creditos, nota, estado, tipologia, periodo)
_PRUEBA1 = [
    # Admitido 2024-2S. Caso: nivelación de matemáticas, materias por suficiencia, repitencias.
    ("1000001", "Matemáticas Básicas", 4, 2.9, R, E, "2024-2S"),
    ("4100925", "Programación en Ingeniería", 2, 3.8, A, B, "2024-2S"),
    ("4100839", "Química General I", 3, 3.7, A, B, "2024-2S"),
    ("4100826", "Introducción a la Ingeniería Química", 2, 4.4, A, Cd, "2024-2S"),
    ("4100684", "Sociología Industrial", 2, 3.0, A, O, "2024-2S"),
    ("1000089", "Cátedra Nacional de Inducción y Preparación para la Vida Universitaria", 2, None, A, L, "2024-2S"),
    ("1000004", "Cálculo Diferencial", 4, 3.3, A, B, "2024-2S"),
    ("1000005", "Cálculo Integral", 4, 2.0, R, B, "2025-1S"),
    ("4100921", "Fundamentos de Economía", 2, 4.9, A, B, "2025-1S"),
    ("4100840", "Química General II", 3, 3.1, A, B, "2025-1S"),
    ("4100831", "Laboratorio de Química General", 2, 4.2, A, B, "2025-1S"),
    ("1000019", "Física: Mecánica", 4, 3.6, A, B, "2025-1S"),
    ("1000005", "Cálculo Integral", 4, 4.4, A, B, "2025-2S"),
    ("4100930", "Termodinámica I", 4, 3.1, A, Cd, "2025-2S"),
    ("4100838", "Química Analítica", 3, 4.3, A, B, "2025-2S"),
    ("4100830", "Laboratorio de Química Analítica", 2, 4.4, A, B, "2025-2S"),
    ("4100584", "Higiene y Seguridad Industrial", 3, 4.2, A, T, "2025-2S"),
    ("1000044", "Inglés I", 3, None, A, E, "2025-2S"),
    ("1000045", "Inglés II", 3, None, A, E, "2025-2S"),
    ("1000046", "Inglés III", 3, None, A, E, "2025-2S"),
    ("1000047", "Inglés IV", 3, None, A, E, "2025-2S"),
    ("1000020", "Física: Oscilaciones, Ondas y Óptica", 4, 2.5, R, O, "2025-2S"),
    ("4100841", "Química Orgánica", 3, 2.2, R, B, "2026-1S"),
    ("4100931", "Termodinámica II", 4, 3.0, A, Cd, "2026-1S"),
    ("4100926", "Biología Celular y Microbiología", 2, 3.3, A, B, "2026-1S"),
    ("1000003", "Álgebra Lineal", 4, None, C, B, "2026-2S"),
    ("1000006", "Cálculo Vectorial", 4, None, C, B, "2026-2S"),
    ("4100836", "Principios de los Procesos Químicos", 3, None, C, Cd, "2026-2S"),
    ("4100841", "Química Orgánica", 3, None, C, B, "2026-2S"),
    ("4100842", "Humanidades para Ingenierías", 2, None, C, B, "2026-2S"),
    ("4100923", "Mecánica de Fluidos", 3, None, C, Cd, "2026-2S"),
]

_PRUEBA2 = [
    # Admitida 2022-1S, 81 % de avance. Caso: estudiante avanzada (la transición no le conviene).
    ("1000004", "Cálculo Diferencial", 4, 4.0, A, B, "2022-1S"),
    ("4100925", "Programación en Ingeniería", 2, 4.6, A, B, "2022-1S"),
    ("4100839", "Química General I", 3, 5.0, A, B, "2022-1S"),
    ("4100826", "Introducción a la Ingeniería Química", 2, 4.7, A, Cd, "2022-1S"),
    ("4100684", "Sociología Industrial", 2, 5.0, A, O, "2022-1S"),
    ("1000089", "Cátedra Nacional de Inducción y Preparación para la Vida Universitaria", 2, None, A, L, "2022-1S"),
    ("1000046", "Inglés III", 3, None, A, E, "2022-1S"),
    ("1000045", "Inglés II", 3, None, A, E, "2022-1S"),
    ("1000044", "Inglés I", 3, None, A, E, "2022-1S"),
    ("1000003", "Álgebra Lineal", 4, 3.3, A, B, "2022-2S"),
    ("4100842", "Humanidades para Ingenierías", 2, 5.0, A, B, "2022-2S"),
    ("4100840", "Química General II", 3, 4.5, A, B, "2022-2S"),
    ("4100831", "Laboratorio de Química General", 2, 4.1, A, B, "2022-2S"),
    ("1000019", "Física: Mecánica", 4, 4.2, A, B, "2022-2S"),
    ("1000005", "Cálculo Integral", 4, 3.0, A, B, "2022-2S"),
    ("1000017", "Física: Electricidad y Magnetismo", 4, 4.5, A, O, "2023-1I"),
    ("1000006", "Cálculo Vectorial", 4, 4.4, A, B, "2023-1S"),
    ("4100838", "Química Analítica", 3, 5.0, A, B, "2023-1S"),
    ("4100830", "Laboratorio de Química Analítica", 2, 4.5, A, B, "2023-1S"),
    ("1000047", "Inglés IV", 3, None, A, E, "2023-1S"),
    ("1000013", "Probabilidad y Estadística", 3, 4.3, A, B, "2023-1S"),
    ("1000007", "Ecuaciones Diferenciales", 4, 4.5, A, B, "2023-2S"),
    ("4101191", "Dibujo Asistido por Computador", 3, 4.6, A, T, "2023-2S"),
    ("4100930", "Termodinámica I", 4, 4.3, A, Cd, "2023-2S"),
    ("4100926", "Biología Celular y Microbiología", 2, 4.7, A, B, "2023-2S"),
    ("4100921", "Fundamentos de Economía", 2, 4.7, A, B, "2023-2S"),
    ("4100841", "Química Orgánica", 3, 4.3, A, B, "2023-2S"),
    ("2026274", "Bogotá Musical Internacional", 3, 4.8, A, L, "2024-1S"),
    ("4200715", "Cátedra Constitución Política e Instrucción Cívica", 3, 4.8, A, L, "2024-1S"),
    ("4100931", "Termodinámica II", 4, 3.9, A, Cd, "2024-1S"),
    ("4100928", "Métodos Numéricos Aplicados a Ingeniería Química", 3, 3.3, A, B, "2024-1S"),
    ("4100836", "Principios de los Procesos Químicos", 3, 4.5, A, Cd, "2024-1S"),
    ("4100584", "Higiene y Seguridad Industrial", 3, 4.3, A, T, "2024-2S"),
    ("4101229", "Cátedra Ethos", 3, 4.8, A, L, "2024-2S"),
    ("4100932", "Fenómenos de Transferencia", 4, 3.5, A, Cd, "2024-2S"),
    ("4100923", "Mecánica de Fluidos", 3, 3.5, A, Cd, "2024-2S"),
    ("4100890", "Bioquímica", 3, 3.5, A, B, "2024-2S"),
    ("4100832", "Laboratorio de Química Orgánica", 2, 4.7, A, B, "2024-2S"),
    ("4100820", "Cinética y Catálisis", 2, 3.8, A, Cd, "2025-1S"),
    ("4201085", "Ciencia de los Datos", 4, 4.5, A, L, "2025-1S"),
    ("4100929", "Procesos de Transferencia de Calor", 3, 3.2, A, Cd, "2025-1S"),
    ("4100924", "Operaciones con Sólidos", 3, 4.0, A, Cd, "2025-1S"),
    ("4100837", "Procesos de Separación", 4, 3.6, A, Cd, "2025-1S"),
    ("1000129", "Cátedra Colombiana: Ciudadanía, Integridad y Lucha contra la Corrupción", 3, 5.0, A, L, "2025-2S"),
    ("4101244", "Problemática Ambiental", 3, 4.9, A, L, "2025-2S"),
    ("4101090", "Diseño de Plantas", 4, 4.6, A, L, "2025-2S"),
    ("4100828", "Laboratorio de Ingeniería Química I", 2, 3.8, A, Cd, "2025-2S"),
    ("4100823", "Ingeniería de las Reacciones Químicas", 3, 4.8, A, Cd, "2025-2S"),
    ("2027937", "Cátedra de Ingeniería Julio Garavito Armero", 3, 4.8, A, L, "2026-1S"),
    ("4200337", "Calidad de Agua", 3, 4.7, A, T, "2026-1S"),
    ("4100844", "Control de Procesos", 4, 5.0, A, Cd, "2026-1S"),
    ("4100825", "Ingeniería de Procesos I", 3, 3.4, A, Cd, "2026-1S"),
    ("4010168", "Contexto: Comunicación y Conflicto Armado", 3, None, C, L, "2026-2S"),
    ("4100882", "Trabajo de Grado", 6, None, C, P, "2026-2S"),
    ("4200269", "Cátedra Gabriel García Márquez", 3, None, C, L, "2026-2S"),
    ("4200338", "Ingeniería Ambiental", 3, None, C, T, "2026-2S"),
]

_PRUEBA3 = [
    # Admitido 2026-1S directamente en la malla nueva: no requiere transición.
    ("1000004", "Cálculo Diferencial", 4, 4.1, A, B, "2026-1S"),
    ("1000003", "Álgebra Lineal", 4, 3.6, A, B, "2026-1S"),
    ("4100826", "Introducción a la Ingeniería Química", 2, 4.0, A, Cd, "2026-1S"),
    ("4100842", "Humanidades para Ingeniería", 2, 4.5, A, B, "2026-1S"),
    ("NUEVO01", "Química General", 3, 3.2, A, B, "2026-1S"),
    ("4100831", "Laboratorio de Química General", 2, 3.8, A, B, "2026-1S"),
    ("1000005", "Cálculo Integral", 4, None, C, B, "2026-2S"),
    ("1000019", "Física: Mecánica", 4, None, C, B, "2026-2S"),
    ("4100841", "Química Orgánica", 3, None, C, B, "2026-2S"),
    ("4100832", "Laboratorio de Química Orgánica", 2, None, C, B, "2026-2S"),
]

MATERIAS_VISTAS = (
    [("20242001", *fila) for fila in _PRUEBA1]
    + [("20221001", *fila) for fila in _PRUEBA2]
    + [("20261001", *fila) for fila in _PRUEBA3]
)

# (username, contraseña, nombre, rol, activo, codigo_estudiante)
USUARIOS = [
    ("admin", "Admin2025*", "Administrador", "admin", True, ""),
    ("consultor", "Consulta2025*", "Consultor Académico", "consultor", True, ""),
    ("inactivo", "Inactivo2025*", "Usuario Inactivo", "consultor", False, ""),
    ("20242001", "Estudiante2026*", "Estudiante Prueba Uno", "estudiante", True, "20242001"),
    ("20221001", "Estudiante2026*", "Estudiante Prueba Dos", "estudiante", True, "20221001"),
    ("20261001", "Estudiante2026*", "Estudiante Prueba Tres", "estudiante", True, "20261001"),
]
