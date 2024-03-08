import spacy

from chat.prompt_handler import prompt_handler
from chat.query_types import PromptResponse
from utils.annotation_types import AnnotationTypes

# Load the English NLP model
nlp = spacy.load("en_core_web_md")


def prompt_ner(text_prediction):
    # Get the model
    selected_text = text_prediction.get_text()
    model = None

    # do ner using spacy
    doc = nlp(selected_text)
    entities = []
    for ent in doc.ents:
        entities.append(f"'{ent.text}' ({ent.label_})")

    prompt = " ".join(entities)

    # Get the 'ner' component from the loaded model's pipeline
    ner = nlp.get_pipe("ner")

    debug_info = {"model_name": "en_core_web_md", "library_name": "spacy"}
    labels_dict = {"labels": f"{ner.labels}"}  # labels are the list of annotations
    return PromptResponse(
        response=prompt, prompt=selected_text, debug_info=debug_info, gpt_model=model, information=labels_dict
    )


def handler(event, _):
    return prompt_handler(event, prompt_ner, AnnotationTypes.NER)
