$heartIcon = $('.fa-heart')
$newWarbleBtn = $('#new-warble')
$closeWarbleBtn = $('#close-warble')

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


$newWarbleBtn.on('click', () => {
    $('#exampleModalCenter').show();
})

$closeWarbleBtn.on('click', () => {
    $('#exampleModalCenter').hide();
})