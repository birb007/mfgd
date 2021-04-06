/* taken from https://docs.djangoproject.com/en/3.1/ref/csrf/#ajax */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function update_desc(url) {
    const json = JSON.stringify({
        "action":"update_description",
        "description" : $("#description").val(),
    });
    const success = "Successfully changed description";
    make_request(url, json, success);
}

function publicize(url, box) {
    const json = JSON.stringify({
        "action": "publicize",
        "public": box.checked
    });
    const success = "Successfully changed gobal visibility";
    make_request(url, json, success);
}

function update_perm(url, box) {
    const [user_id, category] = box.id.split("-");
    const name = $(`#${user_id}-name`).text();

    if (!box.checked && category === "visibility") {
        $(`#${user_id}-management`)[0].checked = box.checked;
    } else if (box.checked && category === "management") {
        $(`#${user_id}-visibility`)[0].checked = box.checked;
    }

    const json = JSON.stringify({
        "action": "update_perm",
        "id": user_id,
        "visible": $(`#${user_id}-visibility`)[0].checked,
        "manage": $(`#${user_id}-management`)[0].checked,
    });
    const success = "Successfully updated permissions for user: " + name;
    make_request(url, json, success);
}

function make_request(url, payload, success) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken === null) {
        console.log("csrftoken not present");
        return;
    }

    $.ajax({
        method: "POST",
        url: url,
        headers: {"X-CSRFToken": csrfToken},
        contentType: "application/json; charset=utf-8",
        data: payload,
        success : result => {
            $("#serv-msg").text(success);
        },
        error: (xhr, status, error) => {
            $("#serv-msg").text(xhr.statusText);
        },
    });
}
