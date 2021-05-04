$heartIcon = $('.fa-heart')

$heartIcon.on('click', async (evt) => {
    let msgId = $(evt.target).data('msgid')
    resp = await axios.post(`/messages/${msgId}/likes`)
    toggleIcon($(evt.target))
})

function toggleIcon($icon) {
    let numLikes = +$('.stat-likes').text();
    let path = window.location.pathname;
    if($icon.hasClass('far')) {
        $icon.removeClass('far')
        $icon.addClass('fas')
        if(path === '/') $('.stat-likes').text(numLikes + 1);
    } else {
        $icon.removeClass('fas');
        $icon.addClass('far');
        if(path === '/') $('.stat-likes').text(numLikes - 1);
    }
}


//add event listener for new message button
//on click, get request? to show form modal, append form to modal
//form on submit- post to messages/new 
//request route to get form info to send back form data to append to modal