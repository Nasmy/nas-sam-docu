import os
from datetime import datetime

from loguru import logger

from aws.aws_s3 import S3Wrapper
from db.tables import UserAttributes, UserDetails, Users
from utils.custom_exceptions import RaiseCustomException


dd_s3 = S3Wrapper()
bucket_name = os.getenv("bucket")


def get_user_details(session, username, filter_str=None):
    result = (
        session.query(
            UserAttributes.attribute_name,
            UserDetails.value,
        )
        .join(UserAttributes, UserAttributes.id == UserDetails.user_attribute_id)
        .join(Users, Users.id == UserDetails.user_id)
        .filter(Users.username == username)
        .all()
    )

    user_data = dict()
    for db_attribute_name, db_value in result:
        if filter_str and filter_str not in db_attribute_name:
            continue
        user_data[db_attribute_name] = db_value

    return user_data


def set_user_details(session, user_id, data_dict):
    result = session.query(UserAttributes.attribute_name, UserAttributes.id).all()
    attribute_name_dict = {ele[0]: ele[1] for ele in result} if result else {}
    logger.info(f"attribute_name_dict: {attribute_name_dict}")

    created_attributes_list = []
    updated_attributes_list = []

    for attribute_name, attribute_data in data_dict.items():
        logger.info(f"attribute_name: {attribute_name} attribute_data: {attribute_data}")

        if attribute_data is None:
            logger.info(f"attribute[{attribute_name}] is None, keeping as is")
            continue

        if attribute_name in attribute_name_dict:
            attribute_id = attribute_name_dict[attribute_name]
        else:
            logger.info(f"attribute[{attribute_name}] not in list")
            new_attribute = UserAttributes(attribute_name=attribute_name)
            session.add(new_attribute)
            session.flush()
            attribute_id = new_attribute.id
            logger.info(f"added new attribute[{attribute_name}]")

        db_user_details = (
            session.query(UserDetails)
            .filter(UserDetails.user_id == user_id)
            .filter(UserDetails.user_attribute_id == attribute_id)
            .first()
        )

        # Check attribute data is base 64 or not
        is_base64 = False
        if attribute_data.startswith("data:"):
            # If base64, store in s3 and return public url
            import cv2 # import here because some functions don't need cv2 aka don't use base64
            from utils.dd_base64 import get_image_from_base_64_string
            try:
                cv_image = get_image_from_base_64_string(attribute_data)
                logger.info(f"Image shape: {cv_image.shape}")
            except Exception as e:
                logger.exception(e)
                raise RaiseCustomException(400, f"Error in base64 data: {attribute_name}")
            temp_file_path = "/tmp/temp_file.jpg"
            cv2.imwrite(temp_file_path, cv_image)
            file_key = f"{user_id}/{attribute_name}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"
            dd_s3.s3_put_object(bucket=bucket_name, key=file_key, body=open(temp_file_path, "rb"))
            os.remove(temp_file_path)
            attribute_data = dd_s3.s3_set_public(bucket_name, file_key)
            is_base64 = True

        if not db_user_details:
            db_user_details = UserDetails(
                user_id=user_id,
                user_attribute_id=attribute_id,
                value=attribute_data,
            )
            session.add(db_user_details)
            logger.info(f"added new user detail[{attribute_name}]: {attribute_data}")
            created_attributes_list.append(attribute_name)
        else:
            if db_user_details.value != attribute_data or is_base64:
                logger.info(f"updated user detail[{attribute_name}]: {db_user_details.value} > {attribute_data}")
                db_user_details.value = attribute_data
                updated_attributes_list.append(attribute_name)
            else:
                logger.info(f"no change in user detail[{attribute_name}]: {db_user_details.value}")

    return created_attributes_list, updated_attributes_list
