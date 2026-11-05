"""Seed ficticio (RN-GL-02) para C-02. Idempotente por email/nombre."""

from __future__ import annotations

from sqlalchemy import select

from app.models import Consultorio, Paciente, Sillon, Tratamiento, Usuario

PLACEHOLDER_PASSWORD_HASH = "placeholder-hash-c02"


async def seed_demo(session) -> None:
    # Consultorio demo
    result = await session.execute(
        select(Consultorio).where(Consultorio.nombre == "Consultorio demo")
    )
    consultorio = result.scalar_one_or_none()
    if consultorio is None:
        consultorio = Consultorio(nombre="Consultorio demo")
        session.add(consultorio)
        await session.flush()

    # Sillones activos
    for nombre in ("Sillón 1", "Sillón 2"):
        result = await session.execute(
            select(Sillon).where(Sillon.nombre == nombre, Sillon.consultorio_id == consultorio.id)
        )
        if result.scalar_one_or_none() is None:
            session.add(Sillon(consultorio_id=consultorio.id, nombre=nombre))

    # Tratamientos
    tratamientos = (("Limpieza", 30, 500000), ("Control", 15, 250000), ("Conducto", 60, 1200000))
    for nombre, duracion, precio in tratamientos:
        result = await session.execute(select(Tratamiento).where(Tratamiento.nombre == nombre))
        if result.scalar_one_or_none() is None:
            session.add(
                Tratamiento(
                    nombre=nombre,
                    duracion_min=duracion,
                    precio_referencia_centavos=precio,
                )
            )

    # Usuarios
    users = (
        ("secretaria.demo@example.com", "secretaria"),
        ("odontologo.demo@example.com", "odontologo"),
        ("paciente.demo@example.com", "paciente"),
    )
    user_by_rol: dict[str, Usuario] = {}
    for email, rol in users:
        result = await session.execute(select(Usuario).where(Usuario.email == email))
        usuario = result.scalar_one_or_none()
        if usuario is None:
            usuario = Usuario(email=email, password_hash=PLACEHOLDER_PASSWORD_HASH, rol=rol)
            session.add(usuario)
            await session.flush()
        user_by_rol[rol] = usuario

    # Paciente vinculado al usuario paciente
    paciente_user = user_by_rol["paciente"]
    result = await session.execute(select(Paciente).where(Paciente.usuario_id == paciente_user.id))
    if result.scalar_one_or_none() is None:
        session.add(
            Paciente(
                usuario_id=paciente_user.id,
                nombre="Paciente Demo",
                telefono="+54 9 11 0000-0000",
                obra_social="Obra social demo",
                notas="Paciente de prueba (ficticio)",
            )
        )

    await session.commit()
