import os

from loguru import logger

from aws.aws_s3 import S3Wrapper
from chat.query_types import ContextTypes
from utils.annotation_types import AnnotationTypes
from validator import validate_page_block_list


class ContextLoader:
    def __init__(self, user_id, doc_id, context_dict):
        self.user_id = user_id
        self.doc_id = doc_id
        self.context_dict = context_dict
        self.s3_dd = S3Wrapper()

        self.input_bucket = os.getenv("files_digest_bucket")

    def load_context_and_type(self):
        context_type = self.context_dict.get("context_type", None)
        logger.info(f"context_type: {context_type}")
        if context_type in list(ContextTypes):
            context = self.load_context(context_type)
        else:
            logger.error(f"invalid context_type: {context_type}")
            context = None
        return context, context_type

    def load_context(self, context_type):
        if context_type == ContextTypes.BLOCKS.value:
            page_block_list = self.context_dict.get("blocks", None)
            if page_block_list:
                logger.info(f"page_block_list: {page_block_list}")
                return self.block_context(page_block_list)
            else:
                logger.error(f"invalid page_block_list: {page_block_list}")
                return None

        elif context_type == ContextTypes.TEXT.value:
            text = self.context_dict.get("text", None)
            if text:
                logger.info(f"text: {text}")
                return self.text_context(text)
            else:
                logger.error(f"invalid text: {text}")
                return None

        elif context_type == ContextTypes.QUESTION.value:
            question = self.context_dict.get("question", None)
            if question:
                logger.info(f"question: {question}")
                return self.question_context(question)
            else:
                logger.error(f"invalid question: {question}")
                return None

        elif context_type == ContextTypes.HEADINGS.value:
            headings = self.context_dict.get("headings", None)
            if headings and isinstance(headings, list):
                logger.info(f"headings: {headings}")
                return self.headings_context(headings)
            else:
                logger.error(f"invalid headings: {headings}")
                return None
        elif context_type == ContextTypes.FULL.value:
            return self.full_context_chat()

    def headings_context(self, heading_keys: list):
        chat_context = dict()
        chat_context["conversation"] = []
        try:
            digest_file_key = f"{self.user_id}/{self.doc_id}/{self.doc_id}-{AnnotationTypes.HEADINGS.value}.json"
            full_headings_json, _ = self.s3_dd.s3_get_json(bucket=self.input_bucket, key=digest_file_key)

            context_headings = []
            context_summaries = []
            for hs in full_headings_json["details"]["response"]["headings"]:
                hed_key = list(hs.keys())[0]
                if hed_key in heading_keys:
                    context_headings.append(hs[hed_key])
                    context_summaries.append(hs[f"S{hed_key[1:]}"])

            if len(context_headings) > 0:
                logger.info(f"context_headings: {context_headings}")
                chat_context["conversation"].append({"role": "user", "content": "Consider the following context"})
                for heading, summary in zip(context_headings, context_summaries):
                    chat_context["conversation"].append({"role": "user", "content": f"{heading} - {summary}"})
                chat_context["conversation"].append({"role": "user", "content": "Then answer following questions"})
                return chat_context
            else:
                logger.error(f"invalid heading_keys: {heading_keys}")
                return None
        except Exception as e:
            logger.exception(f"document: {self.doc_id} with error")
            logger.exception(e)
            return None

    def question_context(self, question_key: str):
        chat_context = dict()
        chat_context["conversation"] = []
        try:
            digest_file_key = f"{self.user_id}/{self.doc_id}/{self.doc_id}-{AnnotationTypes.QUESTIONS.value}.json"
            full_questions_json, _ = self.s3_dd.s3_get_json(bucket=self.input_bucket, key=digest_file_key)

            for hs in full_questions_json["details"]["response"]["questions"]:
                if list(hs.keys())[0] == question_key:
                    question = hs[question_key]
                    answer = hs[f"A{question_key[1:]}"]
                    break
            else:
                logger.error(f"invalid question_key: {question_key}")
                return None
            if question:
                return {
                    "question": question,
                    "answer": answer,
                }
            else:
                logger.error(f"invalid question_key: {question_key}")
                return None
        except Exception as e:
            logger.exception(f"document: {self.doc_id} with error")
            logger.exception(e)
            return None

    def full_context_chat(self):
        chat_context = dict()
        chat_context["conversation"] = []
        digest_file_key = f"{self.user_id}/{self.doc_id}/{self.doc_id}-{AnnotationTypes.ALL_TEXT.value}.json"
        all_text_json, _ = self.s3_dd.s3_get_json(bucket=self.input_bucket, key=digest_file_key)
        all_text = all_text_json["details"]["response"]["text"]
        chat_context["conversation"].append(
            {"role": "user", "content": f"Consider the following context: {all_text[:10000]} - and answer"}
        )
        return chat_context

    def text_context(self, text):
        chat_context = dict()
        chat_context["conversation"] = []
        chat_context["conversation"].append(
            {"role": "user", "content": f"Consider the following context ({text}) and answer"}
        )
        return chat_context

    def block_context(self, block_input):
        chat_context = dict()
        chat_context["conversation"] = []
        try:
            if block_input and validate_page_block_list(block_input):
                digest_file_key = (
                    f"{self.user_id}/{self.doc_id}/{self.doc_id}-{AnnotationTypes.BOUNDING_BOX.value}.json"
                )
                full_json, _ = self.s3_dd.s3_get_json(bucket=self.input_bucket, key=digest_file_key)
                block_context = full_json["details"]["response"]
                block_text = []
                # page_block_list sort by page_no, block_no
                sorted_list = sorted(block_input, key=lambda x: (x[0], x[1]))
                for page_no, block_no in sorted_list:
                    block_text.append(block_context["pages"][page_no]["blocks"][block_no]["text"])
                all_text = " ".join(block_text)
                chat_context["conversation"].append(
                    {"role": "user", "content": f"Consider the following context ({all_text}) and answer"}
                )
                return chat_context
            else:
                logger.error(f"invalid block_input: {block_input}")
                return None
        except Exception as e:
            logger.exception(f"document: {self.doc_id} with error")
            logger.exception(e)
            return None

    @staticmethod
    def context_length(chat_context):
        if chat_context is None:
            return 0
        all_words = [len(x["content"].split()) for x in chat_context["conversation"]]
        return sum(all_words)
